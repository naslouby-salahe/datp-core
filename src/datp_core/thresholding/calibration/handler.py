"""Calibration subsampling stage handler."""

from __future__ import annotations

from typing import SupportsInt, cast

from io import BytesIO

import polars as pl

from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.pipeline.stages.context import EvaluationContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.outcomes import StageJobOutcome
from datp_core.thresholding.calibration.sampling import subsample_calibration_scores
from datp_core.thresholding.policies.enums import CalibrationNestingPolicy, CalibrationSelectionStrategy


_NEVER_THRESHOLDS_ONLY_RECOMPUTED = "never_thresholds_only_recomputed"
_DERIVED_SEED_ALGORITHM_CALIBRATION_SUBSAMPLE = "derived_seed_algorithm_with_namespace_calibration_subsample"


class CalibrationSubsamplingStageHandler:
    stage = StageKind.CALIBRATION_SUBSAMPLING

    def __init__(self, config: ResolvedProjectConfiguration, store: ArtifactStore) -> None:
        self._config = config
        self._store = store

    def execute(self, job: StageJob) -> StageJobOutcome:
        assert isinstance(job.context, EvaluationContext)
        ctx = job.context
        if ctx.seed is None or ctx.calibration_sample_count is None or ctx.calibration_replicate is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Calibration subsampling requires a seed, sample count, and replicate",
            )
        experiment = self._config.experiments.get(ctx.experiment_id)
        subset = experiment.calibration_subset
        if subset is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Calibration subsampling is not configured for this experiment",
            )
        if (
            subset.selection_strategy != CalibrationSelectionStrategy.DETERMINISTIC_WITHOUT_REPLACEMENT
            or subset.nesting_policy != CalibrationNestingPolicy.NESTED_BY_SIZE
            or subset.model_retraining != _NEVER_THRESHOLDS_ONLY_RECOMPUTED
            or subset.replicate_seed_derivation != _DERIVED_SEED_ALGORITHM_CALIBRATION_SUBSAMPLE
        ):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Calibration subset contract is not executable by the configured deterministic sampler",
            )
        try:
            namespace = self._config.protocol_determinism.seed_namespaces["calibration_subsample"]
            digest_bytes = int(cast("SupportsInt", self._config.protocol_determinism.derived_seed_algorithm["digest_bytes"]))
            scores = validate_calibration_score_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.input_path("calibration_scores"))))
            )
            sampled = subsample_calibration_scores(
                scores,
                requested_sample_count=ctx.calibration_sample_count,
                training_seed=ctx.seed,
                selection_seed=subset.selection_seed.value,
                replicate=ctx.calibration_replicate,
                namespace_key=namespace.key,
                digest_bytes=digest_bytes,
            )
            payload = BytesIO()
            validate_calibration_score_frame(sampled).write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path("calibration_subset_scores"), payload.getvalue())
        except (KeyError, OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
