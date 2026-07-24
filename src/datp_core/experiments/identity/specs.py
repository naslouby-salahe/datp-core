"""Authoritative identity specification registry — one spec per IdentityKind."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactKind
from datp_core.experiments.identity.kinds import IdentityKind, StageIdentitySpec

_IDENTITY_SPECS: dict[IdentityKind, StageIdentitySpec] = {
    IdentityKind.PREFLIGHT: StageIdentitySpec(
        artifact_kind=ArtifactKind.RESOLVED_CONFIG, job_token="preflight", artifact_token="preflight_status"
    ),
    IdentityKind.MATERIALIZATION: StageIdentitySpec(
        artifact_kind=ArtifactKind.MATERIALIZED_DATASET,
        job_token="mat",
        artifact_token="mat_data",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
    ),
    IdentityKind.TRAINING: StageIdentitySpec(
        artifact_kind=ArtifactKind.MODEL_CHECKPOINT,
        job_token="train",
        artifact_token="checkpoint",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.PERSONALIZED_CHECKPOINT: StageIdentitySpec(
        artifact_kind=ArtifactKind.PERSONALIZED_MODEL_CHECKPOINT,
        job_token="personalized_checkpoint",
        artifact_token="personalized_checkpoint",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.CALIBRATION_SCORE: StageIdentitySpec(
        artifact_kind=ArtifactKind.CALIBRATION_SCORES,
        job_token="calibration_scores",
        artifact_token="calib_scores",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.FUTURE_RECALIBRATION_SCORE: StageIdentitySpec(
        artifact_kind=ArtifactKind.FUTURE_RECALIBRATION_SCORES,
        job_token="future_recalibration_scores",
        artifact_token="future_recalibration_scores",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.TEST_SCORE: StageIdentitySpec(
        artifact_kind=ArtifactKind.TEST_SCORES,
        job_token="test_scores",
        artifact_token="test_scores",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
    ),
    IdentityKind.THRESHOLD: StageIdentitySpec(
        artifact_kind=ArtifactKind.THRESHOLDS,
        job_token="thresh",
        artifact_token="threshold_set",
        uses_seed=True,
        uses_condition=True,
        uses_execution=True,
        uses_calibration_subset=True,
        uses_evaluation_label=True,
    ),
    IdentityKind.EVALUATION: StageIdentitySpec(
        artifact_kind=ArtifactKind.CLIENT_METRICS,
        job_token="eval",
        artifact_token="metrics",
        uses_seed=True,
        uses_condition=True,
        uses_execution=True,
        uses_calibration_subset=True,
        uses_evaluation_label=True,
    ),
    IdentityKind.STATISTICAL_ANALYSIS: StageIdentitySpec(
        artifact_kind=ArtifactKind.STATISTICAL_SUMMARY,
        job_token="statistical_analysis",
        artifact_token="statistical_report",
    ),
    IdentityKind.COHORT_CHECKPOINT_SELECTION: StageIdentitySpec(
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
        job_token="cohort_checkpoint_selection",
        artifact_token="cohort_checkpoint_selection",
    ),
    IdentityKind.FEDERATED_PROXIMAL_SELECTION: StageIdentitySpec(
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
        job_token="federated_proximal_coefficient_selection",
        artifact_token="federated_proximal_coefficient_selection",
    ),
    IdentityKind.DITTO_SELECTION: StageIdentitySpec(
        artifact_kind=ArtifactKind.CHECKPOINT_SELECTION,
        job_token="ditto_proximal_weight_selection",
        artifact_token="ditto_proximal_weight_selection",
    ),
    IdentityKind.REPORT: StageIdentitySpec(
        artifact_kind=ArtifactKind.RESULT_REPORT, job_token="report_generation", artifact_token="final_report"
    ),
    IdentityKind.RESULT_FREEZE: StageIdentitySpec(
        artifact_kind=ArtifactKind.RESULT_FREEZE, job_token="result_freeze", artifact_token="result_freeze"
    ),
    IdentityKind.CALIBRATION_SUBSET: StageIdentitySpec(
        artifact_kind=ArtifactKind.CALIBRATION_SUBSET,
        job_token="calibration_subset",
        artifact_token="calibration_subset",
        uses_seed=True,
        uses_condition=True,
        uses_population=True,
        uses_execution=True,
        uses_calibration_subset=True,
    ),
}
