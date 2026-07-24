"""IdentityKind enum and StageIdentitySpec record."""

from __future__ import annotations

from enum import Enum

from attrs import define

from datp_core.artifacts.identity import ArtifactKind


class IdentityKind(Enum):
    PREFLIGHT = "preflight"
    MATERIALIZATION = "materialization"
    TRAINING = "training"
    PERSONALIZED_CHECKPOINT = "personalized_checkpoint"
    CALIBRATION_SCORE = "calibration_score"
    FUTURE_RECALIBRATION_SCORE = "future_recalibration_score"
    TEST_SCORE = "test_score"
    THRESHOLD = "threshold"
    EVALUATION = "evaluation"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    COHORT_CHECKPOINT_SELECTION = "cohort_checkpoint_selection"
    FEDERATED_PROXIMAL_SELECTION = "federated_proximal_selection"
    DITTO_SELECTION = "ditto_selection"
    REPORT = "report"
    RESULT_FREEZE = "result_freeze"
    CALIBRATION_SUBSET = "calibration_subset"


@define(frozen=True, slots=True, kw_only=True)
class StageIdentitySpec:
    artifact_kind: ArtifactKind
    job_token: str
    artifact_token: str
    uses_seed: bool = False
    uses_condition: bool = False
    uses_population: bool = False
    uses_execution: bool = False
    uses_calibration_subset: bool = False
    uses_evaluation_label: bool = False
