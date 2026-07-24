"""Calibration subsampling pipeline stage handler."""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.identity import ArtifactFormat
from datp_core.artifacts.payloads import BytesPayload
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import RunId
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import score_context
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.thresholding.calibration.sampling import subsample_calibration_scores
from datp_core.thresholding.policies.enums import CalibrationNestingPolicy, CalibrationSelectionStrategy


class CalibrationSubsamplingStageHandler:
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
            subset.selection_strategy != CalibrationSelectionStrategy.DETERMINISTIC_WITHOUT_REPLACEMENT.value
            or subset.nesting_policy != CalibrationNestingPolicy.NESTED_BY_SIZE.value
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
        calibration_relative_path = (
            f"runs/{run_id.value}/{IdentityBuilder.calibration_score_job_id(score_context(context)).value}"
        )
        calibration = self._repository.read(calibration_relative_path)
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
            parents=artifact_parents(self._config, ((job.inputs[0], calibration_relative_path),)),
            payload=BytesPayload(payload_bytes=payload.getvalue()),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                job_id=job.job_id,
                stage=job.stage,
                error_message=commit.error_message or "calibration subset commit failed",
            )
        return StageJobOutcome.succeeded(job_id=job.job_id, stage=job.stage, produced_artifact=job.output)
