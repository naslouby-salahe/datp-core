"""Authoritative identity specification registry — one spec per IdentityKind."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactKind
from datp_core.experiments.identity.kinds import IdentityKind, StageIdentitySpec
from datp_core.pipeline.stages.enums import StageKind

_IDENTITY_SPECS: dict[IdentityKind, StageIdentitySpec] = {
    IdentityKind.PREFLIGHT: StageIdentitySpec(
        stage_kind=StageKind.PREFLIGHT,
        artifact_kind=ArtifactKind.RESOLVED_CONFIG,
    ),
    IdentityKind.MATERIALIZATION: StageIdentitySpec(
        stage_kind=StageKind.DATASET_MATERIALIZATION,
        artifact_kind=ArtifactKind.MATERIALIZED_DATASET,
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
    ),
    IdentityKind.TRAINING: StageIdentitySpec(
        stage_kind=StageKind.MODEL_TRAINING,
        artifact_kind=ArtifactKind.MODEL_CHECKPOINT,
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.PERSONALIZED_CHECKPOINT: StageIdentitySpec(
        stage_kind=StageKind.MODEL_TRAINING,
        artifact_kind=ArtifactKind.PERSONALIZED_MODEL_CHECKPOINT,
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.CALIBRATION_SCORE: StageIdentitySpec(
        stage_kind=StageKind.SCORE_GENERATION,
        artifact_kind=ArtifactKind.CALIBRATION_SCORES,
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.FUTURE_RECALIBRATION_SCORE: StageIdentitySpec(
        stage_kind=StageKind.SCORE_GENERATION,
        artifact_kind=ArtifactKind.FUTURE_RECALIBRATION_SCORES,
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.TEST_SCORE: StageIdentitySpec(
        stage_kind=StageKind.SCORE_GENERATION,
        artifact_kind=ArtifactKind.TEST_SCORES,
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.THRESHOLD: StageIdentitySpec(
        stage_kind=StageKind.THRESHOLD_CONSTRUCTION,
        artifact_kind=ArtifactKind.THRESHOLDS,
        uses_seed=True,
        uses_condition=True,
        uses_execution=True,
        uses_calibration_subset=True,
        uses_evaluation_label=True,
    ),
    IdentityKind.EVALUATION: StageIdentitySpec(
        stage_kind=StageKind.OPERATING_POINT_EVALUATION,
        artifact_kind=ArtifactKind.CLIENT_METRICS,
        uses_seed=True,
        uses_condition=True,
        uses_execution=True,
        uses_calibration_subset=True,
        uses_evaluation_label=True,
    ),
    IdentityKind.STATISTICAL_ANALYSIS: StageIdentitySpec(
        stage_kind=StageKind.STATISTICAL_ANALYSIS,
        artifact_kind=ArtifactKind.STATISTICAL_SUMMARY,
    ),
    IdentityKind.COHORT_CHECKPOINT_SELECTION: StageIdentitySpec(
        stage_kind=StageKind.CHECKPOINT_SELECTION,
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
    ),
    IdentityKind.FEDERATED_PROXIMAL_SELECTION: StageIdentitySpec(
        stage_kind=StageKind.CHECKPOINT_SELECTION,
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
    ),
    IdentityKind.DITTO_SELECTION: StageIdentitySpec(
        stage_kind=StageKind.CHECKPOINT_SELECTION,
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
    ),
    IdentityKind.REPORT: StageIdentitySpec(
        stage_kind=StageKind.REPORT_GENERATION,
        artifact_kind=ArtifactKind.RESULT_REPORT,
    ),
    IdentityKind.RESULT_FREEZE: StageIdentitySpec(
        stage_kind=StageKind.RESULT_FREEZE,
        artifact_kind=ArtifactKind.RESULT_FREEZE,
    ),
    IdentityKind.CALIBRATION_SUBSET: StageIdentitySpec(
        stage_kind=StageKind.CALIBRATION_SUBSAMPLING,
        artifact_kind=ArtifactKind.CALIBRATION_SUBSET,
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
        uses_calibration_subset=True,
    ),
}
