"""Pipeline stages for calibration subsampling, threshold construction, and operating-point evaluation."""

from __future__ import annotations

import json
from io import BytesIO

import polars as pl

from datp_core.application.learning_stages import _score_context
from datp_core.application.stage_protocol import (
    artifact_parents,
    commit_artifact,
)
from datp_core.application.threshold_construction import ConstructThresholdsUseCase
from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.domain.artifacts import (
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactRepository,
    BytesPayload,
)
from datp_core.domain.identifiers import ArtifactId, ClientId, DatasetId, RunId
from datp_core.domain.outcomes import StageJob, StageJobOutcome, StageKind
from datp_core.domain.thresholding import (
    BenignCalibrationScores,
    ThresholdSet,
)
from datp_core.domain.values import Seed
from datp_core.infrastructure.tables.calibration_subsampling import subsample_calibration_scores
from datp_core.infrastructure.tables.polars_engine import compute_client_auroc, compute_operating_point_metrics
from datp_core.infrastructure.tables.schemas import (
    validate_calibration_score_frame,
    validate_client_metric_frame,
    validate_test_score_frame,
    validate_threshold_frame,
)
from datp_core.planning.identity import IdentityBuilder


class CalibrationSubsamplingStageHandler:
    """Persist one nested, benign-only calibration window without retraining or rescoring."""

    stage = StageKind.CALIBRATION_SUBSAMPLING

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        context = job.context
        if context.seed is None or context.calibration_sample_count is None or context.calibration_replicate is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subsampling requires a seed, sample count, and replicate",
            )
        experiment = self._config.experiments.get(context.experiment_id)
        subset = experiment.calibration_subset
        if subset is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subsampling is not configured for this experiment",
            )
        if (
            subset.selection_strategy != "deterministic_without_replacement"
            or subset.nesting_policy != "nested_by_size"
            or subset.model_retraining != "never_thresholds_only_recomputed"
            or subset.replicate_seed_derivation != "derived_seed_algorithm_with_namespace_calibration_subsample"
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Calibration subset contract is not executable by the configured deterministic sampler",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        calibration = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(_score_context(context)).value}"
        )
        if not calibration.found or calibration.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Calibration score artifact is unavailable"
            )
        try:
            namespace = self._config.protocol_determinism.seed_namespaces["calibration_subsample"]
            digest_bytes = int(self._config.protocol_determinism.derived_seed_algorithm["digest_bytes"])
            scores = validate_calibration_score_frame(pl.read_parquet(BytesIO(calibration.payload_bytes)))
            sampled = subsample_calibration_scores(
                scores,
                requested_sample_count=context.calibration_sample_count,
                training_seed=context.seed,
                selection_seed=subset.selection_seed.value,
                replicate=context.calibration_replicate,
                namespace_key=namespace.key,
                digest_bytes=digest_bytes,
            )
            validate_calibration_score_frame(sampled)
        except (KeyError, OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        sampled.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "calibration subset commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


class ThresholdConstructionStageHandler:
    """Construct one configured threshold set from immutable benign calibration scores."""

    stage = StageKind.THRESHOLD_CONSTRUCTION

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        repository: ArtifactRepository,
        thresholds: ConstructThresholdsUseCase,
    ) -> None:
        self._config = config
        self._repository = repository
        self._thresholds = thresholds

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        if job.context.threshold_policy_id is None or job.context.population_id is None or job.context.seed is None:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Threshold construction requires policy, population, and seed",
            )
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        calibration_context = _score_context(
            job.context, retain_calibration_subset=job.context.calibration_sample_count is not None
        )
        if calibration_context.calibration_sample_count is not None:
            calibration_job_id = IdentityBuilder.calibration_subset_job_id(calibration_context)
        elif job.context.recalibration_mode == "one_shot":
            calibration_job_id = IdentityBuilder.future_recalibration_score_job_id(calibration_context)
        else:
            calibration_job_id = IdentityBuilder.calibration_score_job_id(calibration_context)
        calibration = self._repository.read(f"runs/{run_id.value}/{calibration_job_id.value}")
        if not calibration.found or calibration.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Calibration score artifact is unavailable"
            )
        experiment = self._config.experiments.get(job.context.experiment_id)
        population = self._config.populations.get(job.context.population_id)
        dataset = self._config.datasets[DatasetId(population.dataset_id.value)]
        evaluation = next((item for item in experiment.evaluations if item.label == job.context.evaluation_label), None)
        if evaluation is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Evaluation configuration is unavailable"
            )
        if (
            evaluation.overrides
            and job.context.threshold_quantile is None
            and job.context.shrinkage_weight is None
            and job.context.federated_summary_fixed_k is None
            and job.context.fingerprint_features is None
        ):
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message="Sweep-derived threshold overrides require explicit expanded jobs",
            )
        try:
            scores = pl.read_parquet(BytesIO(calibration.payload_bytes))
            validate_calibration_score_frame(scores)
            threshold_set: ThresholdSet | None = None
            if scores.is_empty():
                output = pl.DataFrame(
                    schema={
                        "client_id": pl.String,
                        "threshold": pl.Float64,
                        "owner_kind": pl.String,
                        "effective_lambda": pl.Float64,
                        "cluster_label": pl.Int64,
                        "finite_sample_rank": pl.Int64,
                        "attainability_status": pl.String,
                        "policy_id": pl.String,
                        "target_quantile": pl.Float64,
                    }
                )
            else:
                grouped = tuple(
                    BenignCalibrationScores(
                        client_id=ClientId(str(client_id[0])),
                        values=tuple(float(value) for value in rows["score"].to_list()),
                        population_id=job.context.population_id,
                    )
                    for client_id, rows in scores.group_by("client_id", maintain_order=True)
                )
                threshold_set = self._thresholds.execute(
                    job.context.threshold_policy_id,
                    grouped,
                    job.context.population_id,
                    dict(dataset.field_schema.label_fields.family_map)
                    if dataset.field_schema.label_fields.family_map
                    else None,
                    Seed(job.context.seed),
                    (
                        job.context.shrinkage_weight
                        if job.context.shrinkage_weight is not None
                        else job.context.federated_summary_fixed_k
                    ),
                    job.context.threshold_quantile,
                    job.context.fingerprint_features,
                )
                output = pl.DataFrame(
                    {
                        "client_id": [record.client_id.value for record in threshold_set.values],
                        "threshold": [float(record.threshold) for record in threshold_set.values],
                        "owner_kind": [record.owner for record in threshold_set.values],
                        "effective_lambda": [record.effective_lambda for record in threshold_set.values],
                        "cluster_label": [record.cluster_label for record in threshold_set.values],
                        "finite_sample_rank": [record.finite_sample_rank for record in threshold_set.values],
                        "attainability_status": [
                            None if record.attainability_status is None else record.attainability_status.value
                            for record in threshold_set.values
                        ],
                        "policy_id": [threshold_set.policy_id.value] * len(threshold_set.values),
                        "target_quantile": [threshold_set.target_quantile.value] * len(threshold_set.values),
                    },
                    schema_overrides={
                        "effective_lambda": pl.Float64,
                        "cluster_label": pl.Int64,
                        "finite_sample_rank": pl.Int64,
                        "attainability_status": pl.String,
                    },
                )
            validate_threshold_frame(output)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        output.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "threshold artifact commit failed",
            )
        if threshold_set is not None and threshold_set.diagnostics:
            diagnostics_key = ArtifactKey(
                artifact_id=ArtifactId(f"{job.output.artifact_id.value}:diagnostics"),
                kind=ArtifactKind.THRESHOLD_DIAGNOSTICS,
            )
            diagnostics_relative = f"{relative_path}.diagnostics"
            diagnostics_payload = json.dumps(threshold_set.diagnostics, separators=(",", ":"), sort_keys=True).encode(
                "utf-8"
            )
            diagnostics_commit = commit_artifact(
                self._repository,
                self._config,
                job.context,
                artifact_key=diagnostics_key,
                artifact_format=ArtifactFormat.JSON,
                relative_path=diagnostics_relative,
                parents=artifact_parents(self._config, (job.output,)),
                payload=BytesPayload(payload_bytes=diagnostics_payload),
            )
            if not diagnostics_commit.success:
                return StageJobOutcome.failed(
                    job_id=job.job_id,
                    stage=job.stage,
                    error_message=diagnostics_commit.error_message or "threshold diagnostics commit failed",
                )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)


class OperatingPointEvaluationStageHandler:
    """Evaluate configured thresholds against immutable test scores without score reuse across roles."""

    stage = StageKind.OPERATING_POINT_EVALUATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._repository.assess_reuse(
            relative_path, job.output, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse:
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        thresholds = self._repository.read(f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(job.context).value}")
        scores = self._repository.read(
            f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(_score_context(job.context)).value}"
        )
        if not thresholds.found or thresholds.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Threshold artifact is unavailable"
            )
        if not scores.found or scores.payload_bytes is None:
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Test score artifact is unavailable"
            )
        try:
            threshold_frame = validate_threshold_frame(pl.read_parquet(BytesIO(thresholds.payload_bytes)))
            score_frame = validate_test_score_frame(pl.read_parquet(BytesIO(scores.payload_bytes)))
            evaluation = score_frame.join(threshold_frame.select("client_id", "threshold"), on="client_id", how="left")
            if evaluation["threshold"].null_count() > 0 and job.context.calibration_sample_count is None:
                raise ValueError("Threshold artifact does not cover every scored client")
            eligible = evaluation.filter(pl.col("threshold").is_not_null())
            if eligible.is_empty():
                metrics = _ineligible_client_metrics(evaluation)
            elif evaluation["threshold"].null_count() > 0:
                metrics = pl.concat((compute_operating_point_metrics(eligible), _ineligible_client_metrics(evaluation)))
            else:
                metrics = compute_operating_point_metrics(eligible)
            auroc = compute_client_auroc(score_frame)
            metrics = metrics.join(auroc, on="client_id", how="left")
            metrics = metrics.with_columns(
                pl.lit(job.context.threshold_policy_id.value if job.context.threshold_policy_id else None).alias(
                    "policy_id"
                ),
                pl.lit(job.context.seed).alias("seed"),
            )
            validate_client_metric_frame(metrics)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(job_id=job.job_id, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        metrics.write_parquet(payload)
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(self._config, job.inputs),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "metric artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)



def _ineligible_client_metrics(evaluation):
    import polars as pl
    return (
        evaluation.filter(pl.col("threshold").is_null())
        .select("client_id")
        .unique(maintain_order=True)
        .with_columns(
            pl.lit(0).alias("true_positives"),
            pl.lit(0).alias("false_positives"),
            pl.lit(0).alias("true_negatives"),
            pl.lit(0).alias("false_negatives"),
            pl.lit(None, dtype=pl.Float64).alias("false_positive_rate"),
            pl.lit("unavailable_ineligible_client").alias("false_positive_rate_status"),
            pl.lit(None, dtype=pl.Float64).alias("true_positive_rate"),
            pl.lit("unavailable_ineligible_client").alias("true_positive_rate_status"),
            pl.lit(None, dtype=pl.Float64).alias("balanced_accuracy"),
            pl.lit("unavailable_ineligible_client").alias("balanced_accuracy_status"),
            pl.lit(None, dtype=pl.Float64).alias("macro_f1"),
            pl.lit("unavailable_ineligible_client").alias("macro_f1_status"),
            pl.lit(None, dtype=pl.Float64).alias("auroc"),
            pl.lit("unavailable_ineligible_client").alias("auroc_status"),
        )
    )
