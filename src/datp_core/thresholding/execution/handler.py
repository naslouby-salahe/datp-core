"""Threshold construction from one planner-supplied calibration-score file."""

from __future__ import annotations

from io import BytesIO

import polars as pl

from datp_core.artifacts.schemas.scores import validate_calibration_score_frame
from datp_core.artifacts.schemas.thresholds import validate_threshold_frame
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.project import ResolvedProjectConfiguration
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
        self, config: ResolvedProjectConfiguration, store: ArtifactStore, thresholds: ConstructThresholdsUseCase
    ) -> None:
        self._config = config
        self._store = store
        self._thresholds = thresholds

    def execute(self, job: StageJob) -> StageJobOutcome:
        if job.context.threshold_policy_id is None or job.context.population_id is None or job.context.seed is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Threshold construction requires policy, population, and seed",
            )
        policy = self._config.threshold_policies.get(job.context.threshold_policy_id)
        requires_diagnostics = bool(getattr(policy, "required_diagnostics", ()))
        experiment = self._config.experiments.get(job.context.experiment_id)
        population = self._config.populations.get(job.context.population_id)
        dataset = self._config.datasets[population.dataset_id]
        evaluation = next((item for item in experiment.evaluations if item.label == job.context.evaluation_label), None)
        if evaluation is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Evaluation configuration is unavailable"
            )
        if evaluation.overrides and all(
            value is None
            for value in (
                job.context.threshold_quantile,
                job.context.shrinkage_weight,
                job.context.federated_summary_fixed_k,
                job.context.fingerprint_features,
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
                    job.context.threshold_policy_id,
                    calibration_to_benign_scores(scores, job.context.population_id),
                    job.context.population_id,
                    (
                        dict(dataset.field_schema.label_fields.family_map)
                        if dataset.field_schema.label_fields.family_map
                        else None
                    ),
                    job.context.shrinkage_weight
                    if job.context.shrinkage_weight is not None
                    else job.context.federated_summary_fixed_k,
                    job.context.threshold_quantile,
                    job.context.fingerprint_features,
                )
                frame = threshold_set_to_frame(threshold_set)
            validate_threshold_frame(frame)
            diagnostics = b"{}"
            if threshold_set is not None and threshold_set.diagnostics is not None:
                diagnostics = diagnostics_to_json(threshold_set.diagnostics)
            elif requires_diagnostics:
                raise ValueError(f"Threshold policy '{job.context.threshold_policy_id.value}' requires diagnostics")
            payload = BytesIO()
            frame.write_parquet(payload)
            self._store.write_bytes_atomic(job.output_path("thresholds"), payload.getvalue())
            self._store.write_bytes_atomic(job.output_path("diagnostics"), diagnostics)
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_outputs=job.outputs)
