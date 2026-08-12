from enum import StrEnum

import pytest

from datp_core.core.identifiers import (
    AvailabilityStatus,
    CentralizedModelId,
    CentralizedThresholdMethod,
    CommunicationEstimationMethod,
    ContractSubject,
    DatasetId,
    EffectSizeId,
    EvaluationCohort,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    IntervalMethod,
    MetricId,
    MultiplicityCorrectionId,
    OptimizerId,
    PartitionRole,
    PopulationId,
    PopulationIdentityKind,
    PreparedDataCoordinateKind,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    PublicationStatus,
    RawDatasetDirectory,
    ScoreFrameColumn,
    SerializationFormat,
    SplitProtocolId,
    StatisticalTestId,
    TemporalState,
    TrafficRateEvidenceType,
    TrainingHistoryColumn,
    TrainingModelId,
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
        PopulationIdentityKind,
        frozenset(
            (
                "PHYSICAL_DEVICES",
                "FILE_DEFINED_PSEUDO_CLIENTS",
                "SOURCE_DEFINED_SENSOR_GROUPS",
                "SYNTHETIC_DIRICHLET_CLIENTS",
                "VERIFIED_TEMPORAL_GROUPS",
            )
        ),
    ),
    (
        ExperimentReadiness,
        frozenset(("DECLARED", "EXECUTABLE", "SUPPRESSED", "INFEASIBLE", "BLOCKED")),
    ),
    (ProcessedDataBranch, frozenset(("FEDERATED", "CENTRALIZED_REFERENCE"))),
    (PreparedDataCoordinateKind, frozenset(("CANONICAL", "PROCESSED", "RAW"))),
    (RawDatasetDirectory, frozenset(("NBAIOT", "CICIOT2023", "EDGE_IIOTSET"))),
    (
        PartitionRole,
        frozenset(
            ("TRAIN", "CALIBRATION", "EVALUATION", "FUTURE_RECALIBRATION", "STATIC_REFERENCE_RESERVE", "DISCARDED")
        ),
    ),
    (
        SplitProtocolId,
        frozenset(
            (
                "NON_TEMPORAL_EQUAL_THIRDS",
                "TEMPORAL_HISTORICAL_FUTURE",
                "RANDOM_FRACTIONAL_STATIC_REFERENCE",
                "HISTORICAL_TEMPORAL_GAP",
            )
        ),
    ),
    (
        PreprocessingProtocolId,
        frozenset(
            (
                "FEDERATED_POOLED_MIN_MAX",
                "FEDERATED_CLIENT_LOCAL_STANDARD",
                "CENTRALIZED_POOLED_MIN_MAX",
                "TEST_COLUMN_ORDER_PROJECTION",
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
                "THRESHOLD_ESTIMATOR_SCOPE_SENSITIVITY",
                "CONTROLLED_HETEROGENEITY_SWEEP",
                "FAMILY_AND_GROUPED_GRANULARITY",
                "PER_CLIENT_SCORE_GEOMETRY",
                "HETEROGENEITY_BENEFIT_ASSOCIATION",
                "THRESHOLD_MOVEMENT_TRADEOFF",
                "CALIBRATION_SIZE_ABLATION",
                "CALIBRATION_COLD_START_ONBOARDING",
                "SHARED_CALIBRATION_CONTRIBUTOR_AVAILABILITY",
                "FIXED_SHRINKAGE_CURVE",
                "SIZE_AWARE_SHRINKAGE",
                "PREPROCESSING_GEOMETRY_SENSITIVITY",
                "LOCAL_CONFORMAL_COVERAGE",
                "FEDERATED_BENIGN_STATISTICS_COMPARISON",
                "FEDERATED_QUANTILE_ESTIMATION",
                "FIXED_COEFFICIENT_STATISTICS_SENSITIVITY",
                "EDGE_BENIGN_EQUITY_VALIDATION",
                "CICIOT_FILE_CLIENT_BOUNDARY",
                "FEDPROX_ABSORPTION_STRESS_TEST",
                "FEDAVG_LOCAL_FINE_TUNING",
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
                "FEDAVG_LOCAL_FINE_TUNING",
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
                "FEDERATED_KLL_SHARED_THRESHOLD",
            )
        ),
    ),
    (CentralizedThresholdMethod, frozenset(("POOLED_BENIGN_QUANTILE",))),
    (IntervalMethod, frozenset(("BCA_PAIRED_ARITHMETIC_MEAN",))),
    (StatisticalTestId, frozenset(("WILCOXON_SIGNED_RANK",))),
    (EffectSizeId, frozenset(("MATCHED_PAIRS_RANK_BISERIAL",))),
    (MultiplicityCorrectionId, frozenset(("HOLM",))),
    (
        EvaluationCohort,
        frozenset(("FPR_EVALUABLE", "ATTACK_EVALUABLE", "UNAVAILABLE", "DEPLOYMENT_FALLBACK")),
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
                "AVERAGE_PRECISION",
                "MEAN_FPR",
                "FPR_SAMPLE_STANDARD_DEVIATION",
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
                "RECONSTRUCTION_ERROR",
                "THRESHOLD_VALUE",
                "EMPIRICAL_CUMULATIVE_PROBABILITY",
                "JAIN_FAIRNESS_INDEX",
                "GINI_COEFFICIENT",
            )
        ),
    ),
    (AvailabilityStatus, frozenset(("AVAILABLE", "UNAVAILABLE", "UNDEFINED", "SUPPRESSED", "INFEASIBLE"))),
    (TemporalState, frozenset(("STATIC_REFERENCE", "FROZEN_FUTURE", "RECALIBRATED_FUTURE"))),
    (SerializationFormat, frozenset(("PYDANTIC_JSON", "PARQUET", "SAFETENSORS", "SKOPS"))),
    (
        CommunicationEstimationMethod,
        frozenset(
            (
                "SERIALIZED_MESSAGE_SIZE_ESTIMATE",
                "MEASURED_NETWORK_TRAFFIC",
            )
        ),
    ),
    (TrafficRateEvidenceType, frozenset(("MEASURED", "DATASET_DERIVED", "EXTERNALLY_CITED", "UNAVAILABLE"))),
    (
        ContractSubject,
        frozenset(
            (
                "ARTIFACT_PATH",
                "ATTACK_LABELS",
                "AUTOENCODER",
                "BATCH_SIZE",
                "CALIBRATION",
                "CLIENT",
                "CLIENT_IDENTITY",
                "CONFIRMATORY_LADDER",
                "COORDINATE",
                "CUDA",
                "FEATURES",
                "HELD_OUT_METRICS",
                "LABEL",
                "LOCAL_QUANTILE_MEAN",
                "METRICS",
                "OPTIMIZER",
                "PREPROCESSING",
                "QUANTILE",
                "RECONSTRUCTION_ERROR",
                "ROWS",
                "RUNTIME",
                "SCHEMA",
                "SCORES",
                "SEED",
                "SPLIT",
                "THRESHOLD",
                "THRESHOLD_IDENTITY",
                "THRESHOLD_METHOD",
                "TRAFFIC_RATE",
                "TRAINING",
                "TRAINING_HYPERPARAMETERS",
                "WIDTHS",
            )
        ),
    ),
    (TrainingHistoryColumn, frozenset(("EPOCH", "MEAN_TRAINING_LOSS"))),
    (PublicationStatus, frozenset(("PUBLISHED",))),
    (ScoreFrameColumn, frozenset(("STABLE_ROW_ID", "OUTCOME_LABEL", "ATTACK_FAMILY", "RECONSTRUCTION_ERROR"))),
)


_EXTERNAL_CORPUS_PATH_ENUMS = frozenset({RawDatasetDirectory})


def _values_are_unique(values: tuple[str, ...]) -> bool:
    return len(values) == len(set(values))


def _values_match_domain_style(enum_type: type[StrEnum], values: tuple[str, ...]) -> bool:
    if enum_type in _EXTERNAL_CORPUS_PATH_ENUMS:
        return all(value and "=" not in value and "/" not in value for value in values)
    return all(value.islower() and " " not in value for value in values)


@pytest.mark.parametrize(("enum_type", "expected_members"), EXPECTED_MEMBERS)
def test_enum_member_sets_are_exact_and_unique(enum_type: type[StrEnum], expected_members: frozenset[str]) -> None:
    assert set(enum_type.__members__) == expected_members
    assert len(enum_type.__members__) == len(enum_type)
    values = tuple(member.value for member in enum_type)
    assert _values_are_unique(values)
    assert _values_match_domain_style(enum_type, values)


def test_centralized_and_federated_threshold_methods_are_structurally_separate() -> None:
    assert CentralizedThresholdMethod is not FederatedThresholdMethod
    assert set(CentralizedThresholdMethod).isdisjoint(set(FederatedThresholdMethod))
    assert not isinstance(CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE, FederatedThresholdMethod)
