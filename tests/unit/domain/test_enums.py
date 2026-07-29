from enum import StrEnum
from pathlib import Path

import pytest

from datp_core.domain.enums import (
    AvailabilityStatus,
    CapabilityStatus,
    CentralizedModelId,
    CentralizedThresholdMethod,
    CheckpointStatus,
    ClaimStatus,
    ClusterAssignmentAlgorithm,
    ClusterFeatureStandardization,
    ClusterFingerprintFeature,
    ClusterThresholdAggregation,
    CompletionStatus,
    DatasetId,
    EffectSizeId,
    EvaluationCohort,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    IntervalMethod,
    KMeansInitialization,
    MetricId,
    MultiplicityCorrectionId,
    OptimizerId,
    PopulationId,
    ScientificDecision,
    SerializationFormat,
    SplitId,
    StageId,
    StatisticalTestId,
    TemporalState,
    TrafficRateEvidenceType,
    TrainingModelId,
    WarningCode,
)

EXPECTED_MEMBERS = (
    (DatasetId, frozenset(("NBAIOT", "CICIOT2023", "EDGE_IIOTSET"))),
    (
        PopulationId,
        frozenset(
            (
                "NBAIOT_NATURAL_DEVICES",
                "CICIOT_FILE_CLIENTS",
                "NBAIOT_DIRICHLET_CLIENTS",
                "EDGE_SENSOR_GROUPS",
                "EDGE_TEMPORAL_GROUPS",
            )
        ),
    ),
    (
        EvidenceRole,
        frozenset(
            (
                "ANCHOR_REPRODUCTION",
                "CONFIRMATORY",
                "SUPPORTIVE",
                "MECHANISM",
                "THRESHOLD_VARIANT",
                "EXTERNAL_VALIDATION",
                "TRAINING_STRESS_TEST",
                "APPLICABILITY_BOUNDARY",
                "TEMPORAL_BOUNDARY",
                "EXPLORATORY",
                "OPERATIONAL_TRANSLATION",
            )
        ),
    ),
    (
        ExperimentId,
        frozenset(
            (
                "HISTORICAL_DATP_REPRODUCTION",
                "SHARED_VS_LOCAL_CONFIRMATION",
                "SHARED_CONSTRUCTION_SENSITIVITY",
                "QUANTILE_SENSITIVITY",
                "CONTROLLED_HETEROGENEITY_SWEEP",
                "FAMILY_AND_GROUPED_GRANULARITY",
                "PER_CLIENT_SCORE_GEOMETRY",
                "HETEROGENEITY_BENEFIT_ASSOCIATION",
                "THRESHOLD_MOVEMENT_TRADEOFF",
                "CALIBRATION_SIZE_ABLATION",
                "FIXED_SHRINKAGE_CURVE",
                "SIZE_AWARE_SHRINKAGE",
                "LOCAL_CONFORMAL_COVERAGE",
                "FEDERATED_BENIGN_STATISTICS_COMPARISON",
                "FEDERATED_QUANTILE_ESTIMATION",
                "FIXED_COEFFICIENT_STATISTICS_SENSITIVITY",
                "EDGE_BENIGN_EQUITY_VALIDATION",
                "CICIOT_FILE_CLIENT_BOUNDARY",
                "FEDPROX_ABSORPTION_STRESS_TEST",
                "DITTO_ABSORPTION_STRESS_TEST",
                "EDGE_ONE_SHOT_RECALIBRATION",
                "ALERT_BURDEN_TRANSLATION",
                "GROUP_MEDIAN_SUPPLEMENT",
                "OPTIONAL_EQUITY_INDICES",
            )
        ),
    ),
    (
        TrainingModelId,
        frozenset(
            (
                "FEDAVG_AUTOENCODER",
                "FEDPROX_AUTOENCODER",
                "DITTO_GLOBAL_AUTOENCODER",
                "DITTO_PERSONALIZED_AUTOENCODER",
            )
        ),
    ),
    (CentralizedModelId, frozenset(("CENTRALIZED_AUTOENCODER",))),
    (OptimizerId, frozenset(("ADAM",))),
    (
        FederatedThresholdMethod,
        frozenset(
            (
                "SHARED_THRESHOLD",
                "LOCAL_THRESHOLD",
                "FAMILY_THRESHOLD",
                "CLUSTER_THRESHOLD",
                "POOLED_SHARED_QUANTILE",
                "SAMPLE_WEIGHTED_SHARED_THRESHOLD",
                "LOCAL_GLOBAL_SHRINKAGE",
                "SIZE_AWARE_SHRINKAGE",
                "LOCAL_CONFORMAL_THRESHOLD",
                "FEDERATED_BENIGN_STATISTICS",
            )
        ),
    ),
    (CentralizedThresholdMethod, frozenset(("POOLED_BENIGN_QUANTILE",))),
    (
        ClusterFingerprintFeature,
        frozenset(
            (
                "BENIGN_ERROR_MEAN",
                "BENIGN_ERROR_STANDARD_DEVIATION",
                "BENIGN_ERROR_SKEWNESS",
                "BENIGN_ERROR_P95",
            )
        ),
    ),
    (ClusterFeatureStandardization, frozenset(("STANDARD_SCALER",))),
    (ClusterAssignmentAlgorithm, frozenset(("KMEANS",))),
    (KMeansInitialization, frozenset(("KMEANS_PLUS_PLUS",))),
    (ClusterThresholdAggregation, frozenset(("ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS",))),
    (IntervalMethod, frozenset(("BCA_PAIRED_ARITHMETIC_MEAN",))),
    (StatisticalTestId, frozenset(("WILCOXON_SIGNED_RANK",))),
    (EffectSizeId, frozenset(("MATCHED_PAIRS_RANK_BISERIAL",))),
    (MultiplicityCorrectionId, frozenset(("HOLM",))),
    (
        EvaluationCohort,
        frozenset(("CONFIRMATORY_ELIGIBLE", "ATTACK_EVALUABLE", "UNAVAILABLE", "DEPLOYMENT_FALLBACK")),
    ),
    (
        MetricId,
        frozenset(
            (
                "FALSE_POSITIVE_RATE",
                "TRUE_POSITIVE_RATE",
                "BALANCED_ACCURACY",
                "BINARY_MACRO_F1",
                "AUROC",
                "MEAN_FPR",
                "FPR_POPULATION_STANDARD_DEVIATION",
                "FPR_COEFFICIENT_OF_VARIATION",
                "FPR_IQR",
                "FPR_RANGE",
                "WORST_CLIENT_FPR",
                "TPR_COEFFICIENT_OF_VARIATION",
                "P10_BINARY_MACRO_F1",
                "WORST_CLIENT_BALANCED_ACCURACY",
                "MEAN_CLIENT_MACRO_F1",
                "POOLED_MACRO_F1",
                "MEAN_CLIENT_BALANCED_ACCURACY",
                "ABSOLUTE_THRESHOLD_ERROR",
                "RELATIVE_THRESHOLD_ERROR",
                "SIGNED_ATTAINMENT_ERROR",
                "ABSOLUTE_ATTAINMENT_ERROR",
                "TARGET_COVERAGE",
                "ACHIEVED_COVERAGE",
                "SIGNED_COVERAGE_ERROR",
                "ABSOLUTE_COVERAGE_ERROR",
                "ALERTS_PER_DAY",
                "COMMUNICATION_BYTES",
            )
        ),
    ),
    (AvailabilityStatus, frozenset(("AVAILABLE", "UNAVAILABLE", "UNDEFINED", "SUPPRESSED", "INFEASIBLE"))),
    (CapabilityStatus, frozenset(("SUPPORTED", "UNSUPPORTED", "CONDITIONAL", "UNAVAILABLE", "NOT_APPLICABLE"))),
    (
        ScientificDecision,
        frozenset(
            (
                "SUPPORTED",
                "DIRECTIONAL_INCONCLUSIVE",
                "NO_OBSERVED_ADVANTAGE",
                "OPPOSITE_DIRECTION",
                "PARTIAL_ABSORPTION",
                "FULL_ABSORPTION",
                "BOUNDARY_RESULT",
                "INFEASIBLE",
                "BLOCKED",
            )
        ),
    ),
    (ClaimStatus, frozenset(("PERMITTED", "NARROWED", "BLOCKED", "UNSUPPORTED", "SUPPRESSED"))),
    (
        StageId,
        frozenset(
            (
                "ANALYZE",
                "CALIBRATE",
                "CONSTRUCT_CENTRALIZED_REFERENCE_THRESHOLD",
                "CONSTRUCT_FEDERATED_THRESHOLDS",
                "CONSTRUCT_POPULATION",
                "EVALUATE_CENTRALIZED_REFERENCE",
                "EVALUATE_FEDERATED",
                "FINALIZE",
                "MATERIALIZE",
                "PREFLIGHT",
                "PREPROCESS_CENTRALIZED_REFERENCE",
                "PREPROCESS_FEDERATED",
                "REPORT",
                "SCORE_CENTRALIZED_REFERENCE",
                "SCORE_FEDERATED",
                "SELECT_CENTRALIZED_REFERENCE_CHECKPOINT",
                "SELECT_FEDERATED_CHECKPOINT",
                "SPLIT",
                "TRAIN_CENTRALIZED_REFERENCE",
                "TRAIN_FEDERATED",
                "VERIFY_ANCHOR",
            )
        ),
    ),
    (
        SplitId,
        frozenset(
            (
                "BENIGN_TRAINING",
                "BENIGN_CALIBRATION",
                "HELD_OUT_EVALUATION",
                "HISTORICAL_BENIGN_CALIBRATION",
                "FUTURE_BENIGN_RECALIBRATION",
                "FUTURE_HELD_OUT_EVALUATION",
            )
        ),
    ),
    (TemporalState, frozenset(("STATIC_REFERENCE", "FROZEN_FUTURE", "ONE_SHOT_RECALIBRATED_FUTURE"))),
    (SerializationFormat, frozenset(("PYDANTIC_JSON", "PARQUET", "SAFETENSORS", "SKOPS"))),
    (
        WarningCode,
        frozenset(
            (
                "NEAR_ZERO_MEAN_FPR",
                "UNDEFINED_COEFFICIENT_OF_VARIATION",
                "UNAVAILABLE_ATTACK_ASSIGNMENT",
                "INVALID_TEMPORAL_CHRONOLOGY",
                "UNRESOLVED_CLUSTER_ASSIGNMENTS",
                "MISSING_TRAFFIC_RATE_EVIDENCE",
                "SERIALIZED_MESSAGE_SIZE_ESTIMATE",
            )
        ),
    ),
    (TrafficRateEvidenceType, frozenset(("MEASURED", "DATASET_DERIVED", "EXTERNALLY_CITED", "UNAVAILABLE"))),
    (
        CheckpointStatus,
        frozenset(("HISTORICAL_ENDPOINT", "CANDIDATE", "SELECTED_BY_NON_TEST_RULE", "STABILITY_EVIDENCE")),
    ),
    (CompletionStatus, frozenset(("NOT_STARTED", "IN_PROGRESS", "COMPLETE", "FAILED", "BLOCKED"))),
)


@pytest.mark.parametrize(("enum_type", "expected_members"), EXPECTED_MEMBERS)
def test_enum_member_sets_are_exact_and_unique(enum_type: type[StrEnum], expected_members: frozenset[str]) -> None:
    assert set(enum_type.__members__) == expected_members
    assert len(enum_type.__members__) == len(enum_type)
    values = tuple(member.value for member in enum_type)
    assert len(values) == len(set(values))
    assert all(value.islower() and " " not in value for value in values)


def test_centralized_and_federated_threshold_methods_are_structurally_separate() -> None:
    assert CentralizedThresholdMethod is not FederatedThresholdMethod
    assert set(CentralizedThresholdMethod).isdisjoint(set(FederatedThresholdMethod))
    assert not isinstance(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE, FederatedThresholdMethod)


def test_stage_id_exhaustively_covers_existing_stage_files() -> None:
    stages_root = Path(__file__).parents[3] / "src" / "datp_core" / "orchestration" / "stages"
    stage_files = frozenset(path.stem for path in stages_root.glob("*.py") if path.stem != "__init__")
    assert {stage.value for stage in StageId} == stage_files
