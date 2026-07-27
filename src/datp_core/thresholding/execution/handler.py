"""Threshold construction from one planner-supplied calibration-score file."""

from __future__ import annotations

from io import BytesIO
import polars as pl

from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.pipeline.stages.context import EvaluationContext
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
from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord
from datp_core.thresholding.policies.federated import (
    FederatedFixedCoefficientThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
)


class ThresholdConstructionStageHandler:
    stage = StageKind.THRESHOLD_CONSTRUCTION

    def __init__(
        self, config: ResolvedProjectConfiguration, store: ArtifactStore, thresholds: ConstructThresholdsUseCase
    ) -> None:
        self._config = config
        self._store = store
        self._thresholds = thresholds

    def execute(self, job: StageJob) -> StageJobOutcome:
        assert isinstance(job.context, EvaluationContext)
        ctx = job.context
        if ctx.threshold_policy_id is None or ctx.population_id is None or ctx.seed is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Threshold construction requires policy, population, and seed",
            )
        policy = self._config.threshold_policies.get(ctx.threshold_policy_id)
        requires_diagnostics = (
            policy is not None
            and isinstance(
                policy,
                (
                    FederatedMatchedExceedanceThresholdPolicyRecord,
                    FederatedFixedCoefficientThresholdPolicyRecord,
                    ClusterThresholdPolicyRecord,
                ),
            )
            and bool(policy.required_diagnostics)
        )
        experiment = self._config.experiments.get(ctx.experiment_id)
        population = self._config.populations.get(ctx.population_id)
        dataset = self._config.datasets[population.dataset_id]
        evaluation = next((item for item in experiment.evaluations if item.label == ctx.evaluation_label), None)
        if evaluation is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Evaluation configuration is unavailable"
            )
        if evaluation.overrides and all(
            value is None
            for value in (
                ctx.threshold_quantile,
                ctx.shrinkage_weight,
                ctx.federated_summary_fixed_k,
                ctx.fingerprint_features,
            )
        ):
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Sweep-derived threshold overrides require explicit expanded jobs",
            )
        try:
            scores = validate_calibration_score_frame(
                pl.read_parquet(BytesIO(self._store.read_bytes(job.inputs[0].relative_path)))
            )
            threshold_set = None
            if scores.is_empty():
                frame = empty_threshold_frame()
            else:
                threshold_set = self._thresholds.execute(
                    ctx.threshold_policy_id,
                    calibration_to_benign_scores(scores, ctx.population_id),
                    ctx.population_id,
                    (
                        dict(dataset.field_schema.label_fields.family_map)
                        if dataset.field_schema.label_fields.family_map
                        else None
                    ),
                    ctx.shrinkage_weight if ctx.shrinkage_weight is not None else ctx.federated_summary_fixed_k,
                    ctx.threshold_quantile,
                    ctx.fingerprint_features,
                )
                frame = threshold_set_to_frame(threshold_set)
            validate_threshold_frame(frame)
            diagnostics = b"{}"
            if threshold_set is not None and threshold_set.diagnostics is not None:
                diagnostics = diagnostics_to_json(threshold_set.diagnostics)
            elif requires_diagnostics:
                raise ValueError(f"Threshold policy '{ctx.threshold_policy_id.value}' requires diagnostics")
            payload = BytesIO()
            frame.write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path("thresholds"), payload.getvalue())
            self._store.write_bytes_atomic(job.output_path("diagnostics"), diagnostics)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
