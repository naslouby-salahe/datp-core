"""Threshold construction pipeline stage handler."""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactKind
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ArtifactId, RunId
from datp_core.experiments import RecalibrationMode
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import score_context
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.thresholding.estimation.construction import ConstructThresholdsUseCase
from datp_core.thresholding.execution.frames import (
    calibration_to_benign_scores,
    diagnostics_to_json,
    empty_threshold_frame,
    threshold_set_to_frame,
)


class ThresholdConstructionStageHandler:
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
        calibration_context = score_context(
            job.context, retain_calibration_subset=job.context.calibration_sample_count is not None
        )
        if calibration_context.calibration_sample_count is not None:
            calibration_job_id = IdentityBuilder.calibration_subset_job_id(calibration_context)
        elif job.context.recalibration_mode is RecalibrationMode.ONE_SHOT:
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
        dataset = self._config.datasets[population.dataset_id]
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
            threshold_set = None
            if scores.is_empty():
                output = empty_threshold_frame()
            else:
                grouped = calibration_to_benign_scores(scores, job.context.population_id)
                threshold_set = self._thresholds.execute(
                    job.context.threshold_policy_id,
                    grouped,
                    job.context.population_id,
                    dict(dataset.field_schema.label_fields.family_map)
                    if dataset.field_schema.label_fields.family_map
                    else None,
                    (
                        job.context.shrinkage_weight
                        if job.context.shrinkage_weight is not None
                        else job.context.federated_summary_fixed_k
                    ),
                    job.context.threshold_quantile,
                    job.context.fingerprint_features,
                )
                output = threshold_set_to_frame(threshold_set)
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
        if threshold_set is not None and threshold_set.diagnostics is not None:
            diagnostics_key = ArtifactKey(
                artifact_id=ArtifactId(f"{job.output.artifact_id.value}:diagnostics"),
                kind=ArtifactKind.THRESHOLD_DIAGNOSTICS,
            )
            diagnostics_relative = f"{relative_path}.diagnostics"
            diagnostics_payload = diagnostics_to_json(threshold_set.diagnostics)
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
