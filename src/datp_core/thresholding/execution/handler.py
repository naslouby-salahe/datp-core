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
from datp_core.experiments import RecalibrationMode
from datp_core.experiments.identity import IdentityBuilder
from datp_core.experiments.planning import score_context
from datp_core.pipeline.artifacts.commit import commit_artifact
from datp_core.pipeline.artifacts.lineage import artifact_parents
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import StageNodeKey, node_path
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

    @staticmethod
    def _calibration_node_key(job: StageJob) -> StageNodeKey:
        calibration_context = score_context(
            job.context, retain_calibration_subset=job.context.calibration_sample_count is not None
        )
        if calibration_context.calibration_sample_count is not None:
            return IdentityBuilder.calibration_subset_node_key(calibration_context)
        if job.context.recalibration_mode is RecalibrationMode.ONE_SHOT:
            return IdentityBuilder.future_recalibration_score_node_key(calibration_context)
        return IdentityBuilder.calibration_score_node_key(calibration_context)

    def execute(self, job: StageJob) -> StageJobOutcome:
        if job.context.threshold_policy_id is None or job.context.population_id is None or job.context.seed is None:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message="Threshold construction requires policy, population, and seed",
            )
        relative_path = node_path(job.node_key)
        diagnostics_key = ArtifactKey(
            node_key=job.node_key,
            kind=ArtifactKind.THRESHOLD_DIAGNOSTICS,
        )
        diagnostics_relative = f"{relative_path}.diagnostics"
        policy = self._config.threshold_policies.get(job.context.threshold_policy_id)
        requires_diagnostics = bool(getattr(policy, "required_diagnostics", ()))
        calibration_node_key = self._calibration_node_key(job)
        calibration_relative_path = node_path(calibration_node_key)
        calibration = self._repository.read(calibration_relative_path)
        if not calibration.found or calibration.payload_bytes is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Calibration score artifact is unavailable"
            )
        experiment = self._config.experiments.get(job.context.experiment_id)
        population = self._config.populations.get(job.context.population_id)
        dataset = self._config.datasets[population.dataset_id]
        evaluation = next((item for item in experiment.evaluations if item.label == job.context.evaluation_label), None)
        if evaluation is None:
            return StageJobOutcome.failed(
                node_key=job.node_key, stage=job.stage, error_message="Evaluation configuration is unavailable"
            )
        if (
            evaluation.overrides
            and job.context.threshold_quantile is None
            and job.context.shrinkage_weight is None
            and job.context.federated_summary_fixed_k is None
            and job.context.fingerprint_features is None
        ):
            return StageJobOutcome.failed(
                node_key=job.node_key,
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
            if threshold_set is not None:
                produced_diagnostics = threshold_set.diagnostics is not None
                if requires_diagnostics and not produced_diagnostics:
                    raise ValueError(
                        f"Threshold policy '{job.context.threshold_policy_id.value}' requires diagnostics "
                        "but none were produced"
                    )
                if not requires_diagnostics and produced_diagnostics:
                    raise ValueError(
                        f"Threshold policy '{job.context.threshold_policy_id.value}' produced diagnostics "
                        "it is not configured to require"
                    )
        except (OSError, ValueError) as exc:
            return StageJobOutcome.failed(node_key=job.node_key, stage=job.stage, error_message=str(exc))
        payload = BytesIO()
        output.write_parquet(payload)
        payload_bytes = payload.getvalue()
        commit = commit_artifact(
            self._repository,
            self._config,
            job.context,
            artifact_key=job.output,
            artifact_format=ArtifactFormat.PARQUET,
            relative_path=relative_path,
            parents=artifact_parents(self._config, ((job.inputs[0], calibration_relative_path),)),
            payload=BytesPayload(payload_bytes=payload_bytes),
        )
        if not commit.success:
            return StageJobOutcome.failed(
                node_key=job.node_key,
                stage=job.stage,
                error_message=commit.error_message or "threshold artifact commit failed",
            )
        if threshold_set is not None and threshold_set.diagnostics is not None:
            diagnostics_payload = diagnostics_to_json(threshold_set.diagnostics)
            diagnostics_commit = commit_artifact(
                self._repository,
                self._config,
                job.context,
                artifact_key=diagnostics_key,
                artifact_format=ArtifactFormat.JSON,
                relative_path=diagnostics_relative,
                parents=artifact_parents(self._config, ((job.output, relative_path),)),
                payload=BytesPayload(payload_bytes=diagnostics_payload),
            )
            if not diagnostics_commit.success:
                return StageJobOutcome.failed(
                    node_key=job.node_key,
                    stage=job.stage,
                    error_message=diagnostics_commit.error_message or "threshold diagnostics commit failed",
                )
        return StageJobOutcome.succeeded(node_key=job.node_key, stage=job.stage, produced_artifact=job.output)
