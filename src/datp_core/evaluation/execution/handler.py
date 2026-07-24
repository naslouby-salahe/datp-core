"""Operating-point evaluation stage handler."""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.artifacts.schemas.metrics import validate_client_metric_frame
from datp_core.artifacts.schemas.scores import validate_test_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import RunId
from datp_core.evaluation.metrics.auroc import compute_client_auroc
from datp_core.evaluation.metrics.operating_point import (
    compute_operating_point_metrics,
    ineligible_client_metrics,
)
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import score_context
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome


class OperatingPointEvaluationStageHandler:
    stage = StageKind.OPERATING_POINT_EVALUATION

    def __init__(self, config: ResolvedProjectConfiguration, repository: ArtifactRepository) -> None:
        self._config = config
        self._repository = repository

    def _dependency_reusable(self, relative_path: str, artifact_key: ArtifactKey) -> bool:
        return self._repository.assess_reuse(
            relative_path, artifact_key, self._config.scientific_fingerprint, self._config.execution_fingerprint
        ).can_reuse

    def execute(self, job: StageJob, run_id: RunId) -> StageJobOutcome:
        relative_path = f"runs/{run_id.value}/{job.job_id.value}"
        if self._dependency_reusable(relative_path, job.output):
            return StageJobOutcome.reused(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
        score_ctx = score_context(job.context)
        threshold_path = f"runs/{run_id.value}/{IdentityBuilder.threshold_job_id(job.context).value}"
        score_path = f"runs/{run_id.value}/{IdentityBuilder.test_score_job_id(score_ctx).value}"
        if not self._dependency_reusable(threshold_path, IdentityBuilder.thresholds_key(job.context)):
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Threshold artifact is unavailable or incompatible"
            )
        if not self._dependency_reusable(score_path, IdentityBuilder.test_scores_key(score_ctx)):
            return StageJobOutcome.failed(
                job_id=job.job_id, stage=job.stage, error_message="Test score artifact is unavailable or incompatible"
            )
        thresholds = self._repository.read(threshold_path)
        scores = self._repository.read(score_path)
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
                metrics = ineligible_client_metrics(evaluation)
            elif evaluation["threshold"].null_count() > 0:
                metrics = pl.concat((compute_operating_point_metrics(eligible), ineligible_client_metrics(evaluation)))
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
            parents=artifact_parents(
                self._config,
                (
                    (IdentityBuilder.thresholds_key(job.context), threshold_path),
                    (IdentityBuilder.test_scores_key(score_ctx), score_path),
                ),
            ),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "metric artifact commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
