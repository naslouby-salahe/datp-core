"""DATP-Core closed identities."""

from enum import StrEnum


class DatasetId(StrEnum):
    NBAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"


class PopulationId(StrEnum):
    NBAIOT_NATURAL_DEVICES = "nbaiot_natural_devices"
    CICIOT_FILE_CLIENTS = "ciciot_file_clients"
    NBAIOT_DIRICHLET_CLIENTS = "nbaiot_dirichlet_clients"
    EDGE_SENSOR_GROUPS = "edge_sensor_groups"
    EDGE_TEMPORAL_GROUPS = "edge_temporal_groups"


class PopulationIdentityKind(StrEnum):
    PHYSICAL_DEVICES = "physical_devices"
    FILE_DEFINED_PSEUDO_CLIENTS = "file_defined_pseudo_clients"
    SOURCE_DEFINED_SENSOR_GROUPS = "source_defined_sensor_groups"
    SYNTHETIC_DIRICHLET_CLIENTS = "synthetic_dirichlet_clients"
    VERIFIED_TEMPORAL_GROUPS = "verified_temporal_groups"


class ControlledPartitionKind(StrEnum):
    """Construction kind for controlled synthetic client partitions.

    IID is a separate typed construction condition, never an infinite Dirichlet concentration.
    """

    DIRICHLET = "dirichlet"
    IID = "iid"


class ExperimentReadiness(StrEnum):
    DECLARED = "declared"
    EXECUTABLE = "executable"
    SUPPRESSED = "suppressed"
    INFEASIBLE = "infeasible"
    BLOCKED = "blocked"


class ConfirmatoryDeltaDirection(StrEnum):
    SHARED_MINUS_LOCAL = "shared_minus_local"


class EvidenceRole(StrEnum):
    ANCHOR_REPRODUCTION = "anchor_reproduction"
    CONFIRMATORY = "confirmatory"
    SUPPORTIVE = "supportive"
    MECHANISM = "mechanism"
    THRESHOLD_VARIANT = "threshold_variant"
    EXTERNAL_VALIDATION = "external_validation"
    TRAINING_STRESS_TEST = "training_stress_test"
    APPLICABILITY_BOUNDARY = "applicability_boundary"
    TEMPORAL_BOUNDARY = "temporal_boundary"
    EXPLORATORY = "exploratory"
    OPERATIONAL_TRANSLATION = "operational_translation"


class ExperimentId(StrEnum):
    HISTORICAL_DATP_REPRODUCTION = "historical_datp_reproduction"
    SHARED_VS_LOCAL_CONFIRMATION = "shared_vs_local_confirmation"
    SHARED_CONSTRUCTION_SENSITIVITY = "shared_construction_sensitivity"
    QUANTILE_SENSITIVITY = "quantile_sensitivity"
    CONTROLLED_HETEROGENEITY_SWEEP = "controlled_heterogeneity_sweep"
    FAMILY_AND_GROUPED_GRANULARITY = "family_and_grouped_granularity"
    PER_CLIENT_SCORE_GEOMETRY = "per_client_score_geometry"
    HETEROGENEITY_BENEFIT_ASSOCIATION = "heterogeneity_benefit_association"
    THRESHOLD_MOVEMENT_TRADEOFF = "threshold_movement_tradeoff"
    CALIBRATION_SIZE_ABLATION = "calibration_size_ablation"
    FIXED_SHRINKAGE_CURVE = "fixed_shrinkage_curve"
    SIZE_AWARE_SHRINKAGE = "size_aware_shrinkage"
    LOCAL_CONFORMAL_COVERAGE = "local_conformal_coverage"
    FEDERATED_BENIGN_STATISTICS_COMPARISON = "federated_benign_statistics_comparison"
    FEDERATED_QUANTILE_ESTIMATION = "federated_quantile_estimation"
    FIXED_COEFFICIENT_STATISTICS_SENSITIVITY = "fixed_coefficient_statistics_sensitivity"
    EDGE_BENIGN_EQUITY_VALIDATION = "edge_benign_equity_validation"
    CICIOT_FILE_CLIENT_BOUNDARY = "ciciot_file_client_boundary"
    FEDPROX_ABSORPTION_STRESS_TEST = "fedprox_absorption_stress_test"
    DITTO_ABSORPTION_STRESS_TEST = "ditto_absorption_stress_test"
    EDGE_ONE_SHOT_RECALIBRATION = "edge_one_shot_recalibration"
    ALERT_BURDEN_TRANSLATION = "alert_burden_translation"
    GROUP_MEDIAN_SUPPLEMENT = "group_median_supplement"
    OPTIONAL_EQUITY_INDICES = "optional_equity_indices"


class TrainingModelId(StrEnum):
    FEDAVG_AUTOENCODER = "fedavg_autoencoder"
    FEDPROX_AUTOENCODER = "fedprox_autoencoder"
    DITTO_GLOBAL_AUTOENCODER = "ditto_global_autoencoder"
    DITTO_PERSONALIZED_AUTOENCODER = "ditto_personalized_autoencoder"


class OptimizerId(StrEnum):
    ADAM = "adam"


class CentralizedModelId(StrEnum):
    CENTRALIZED_AUTOENCODER = "centralized_autoencoder"


class FederatedThresholdMethod(StrEnum):
    SHARED_THRESHOLD = "shared_threshold"
    LOCAL_THRESHOLD = "local_threshold"
    FAMILY_THRESHOLD = "family_threshold"
    CLUSTER_THRESHOLD = "cluster_threshold"
    POOLED_SHARED_QUANTILE = "pooled_shared_quantile"
    SAMPLE_WEIGHTED_SHARED_THRESHOLD = "sample_weighted_shared_threshold"
    LOCAL_GLOBAL_SHRINKAGE = "local_global_shrinkage"
    SIZE_AWARE_SHRINKAGE = "size_aware_shrinkage"
    LOCAL_CONFORMAL_THRESHOLD = "local_conformal_threshold"
    FEDERATED_BENIGN_STATISTICS = "federated_benign_statistics"


class ClusterFingerprintFeature(StrEnum):
    BENIGN_ERROR_MEAN = "benign_error_mean"
    BENIGN_ERROR_STANDARD_DEVIATION = "benign_error_standard_deviation"
    BENIGN_ERROR_SKEWNESS = "benign_error_skewness"
    BENIGN_ERROR_P95 = "benign_error_p95"


class ClusterFeatureStandardization(StrEnum):
    STANDARD_SCALER = "standard_scaler"


class ClusterAssignmentAlgorithm(StrEnum):
    KMEANS = "kmeans"


class KMeansInitialization(StrEnum):
    KMEANS_PLUS_PLUS = "kmeans_plus_plus"


class ClusterThresholdAggregation(StrEnum):
    ARITHMETIC_MEAN_OF_ELIGIBLE_LOCAL_THRESHOLDS = "arithmetic_mean_of_eligible_local_thresholds"


class IntervalMethod(StrEnum):
    BCA_PAIRED_ARITHMETIC_MEAN = "bca_paired_arithmetic_mean"


class StatisticalTestId(StrEnum):
    WILCOXON_SIGNED_RANK = "wilcoxon_signed_rank"


class EffectSizeId(StrEnum):
    MATCHED_PAIRS_RANK_BISERIAL = "matched_pairs_rank_biserial"


class MultiplicityCorrectionId(StrEnum):
    HOLM = "holm"


class CentralizedThresholdMethod(StrEnum):
    POOLED_BENIGN_QUANTILE = "pooled_benign_quantile"


class EvaluationCohort(StrEnum):
    CONFIRMATORY_ELIGIBLE = "confirmatory_eligible"
    ATTACK_EVALUABLE = "attack_evaluable"
    UNAVAILABLE = "unavailable"
    DEPLOYMENT_FALLBACK = "deployment_fallback"


class MetricId(StrEnum):
    FALSE_POSITIVE_RATE = "false_positive_rate"
    TRUE_POSITIVE_RATE = "true_positive_rate"
    BALANCED_ACCURACY = "balanced_accuracy"
    BINARY_MACRO_F1 = "binary_macro_f1"
    AUROC = "auroc"
    MEAN_FPR = "mean_fpr"
    FPR_POPULATION_STANDARD_DEVIATION = "fpr_population_standard_deviation"
    FPR_COEFFICIENT_OF_VARIATION = "fpr_coefficient_of_variation"
    FPR_IQR = "fpr_iqr"
    FPR_RANGE = "fpr_range"
    WORST_CLIENT_FPR = "worst_client_fpr"
    TPR_COEFFICIENT_OF_VARIATION = "tpr_coefficient_of_variation"
    P10_BINARY_MACRO_F1 = "p10_binary_macro_f1"
    WORST_CLIENT_BALANCED_ACCURACY = "worst_client_balanced_accuracy"
    MEAN_CLIENT_MACRO_F1 = "mean_client_macro_f1"
    POOLED_MACRO_F1 = "pooled_macro_f1"
    MEAN_CLIENT_BALANCED_ACCURACY = "mean_client_balanced_accuracy"
    ABSOLUTE_THRESHOLD_ERROR = "absolute_threshold_error"
    RELATIVE_THRESHOLD_ERROR = "relative_threshold_error"
    SIGNED_ATTAINMENT_ERROR = "signed_attainment_error"
    ABSOLUTE_ATTAINMENT_ERROR = "absolute_attainment_error"
    TARGET_COVERAGE = "target_coverage"
    ACHIEVED_COVERAGE = "achieved_coverage"
    SIGNED_COVERAGE_ERROR = "signed_coverage_error"
    ABSOLUTE_COVERAGE_ERROR = "absolute_coverage_error"
    ALERTS_PER_DAY = "alerts_per_day"
    COMMUNICATION_BYTES = "communication_bytes"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNDEFINED = "undefined"
    SUPPRESSED = "suppressed"
    INFEASIBLE = "infeasible"


class CapabilityStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    CONDITIONAL = "conditional"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"


class ScientificDecision(StrEnum):
    SUPPORTED = "supported"
    DIRECTIONAL_INCONCLUSIVE = "directional_inconclusive"
    NO_OBSERVED_ADVANTAGE = "no_observed_advantage"
    OPPOSITE_DIRECTION = "opposite_direction"
    PARTIAL_ABSORPTION = "partial_absorption"
    FULL_ABSORPTION = "full_absorption"
    BOUNDARY_RESULT = "boundary_result"
    INFEASIBLE = "infeasible"
    BLOCKED = "blocked"


class ClaimStatus(StrEnum):
    PERMITTED = "permitted"
    NARROWED = "narrowed"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    SUPPRESSED = "suppressed"


class StageId(StrEnum):
    """Eleven high-level pipeline stages. Branch-specific operations use StageOperationId."""

    PREFLIGHT = "preflight"
    DATASET_MATERIALIZATION = "dataset_materialization"
    MODEL_TRAINING = "model_training"
    CHECKPOINT_SELECTION = "checkpoint_selection"
    SCORE_GENERATION = "score_generation"
    CALIBRATION_SUBSAMPLING = "calibration_subsampling"
    THRESHOLD_CONSTRUCTION = "threshold_construction"
    EVALUATION = "evaluation"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    REPORTING = "reporting"
    FINALIZATION = "finalization"


class StageOperationId(StrEnum):
    """Fine-grained stage-file operations under centralized/federated branches."""

    ANALYZE = "analyze"
    CALIBRATE = "calibrate"
    CONSTRUCT_CENTRALIZED_REFERENCE_THRESHOLD = "construct_centralized_reference_threshold"
    CONSTRUCT_FEDERATED_THRESHOLDS = "construct_federated_thresholds"
    CONSTRUCT_POPULATION = "construct_population"
    EVALUATE_CENTRALIZED_REFERENCE = "evaluate_centralized_reference"
    EVALUATE_FEDERATED = "evaluate_federated"
    FINALIZE = "finalize"
    MATERIALIZE = "materialize"
    PREFLIGHT = "preflight"
    PREPROCESS_CENTRALIZED_REFERENCE = "preprocess_centralized_reference"
    PREPROCESS_FEDERATED = "preprocess_federated"
    REPORT = "report"
    SCORE_CENTRALIZED_REFERENCE = "score_centralized_reference"
    SCORE_FEDERATED = "score_federated"
    SELECT_CENTRALIZED_REFERENCE_CHECKPOINT = "select_centralized_reference_checkpoint"
    SELECT_FEDERATED_CHECKPOINT = "select_federated_checkpoint"
    SPLIT = "split"
    TRAIN_CENTRALIZED_REFERENCE = "train_centralized_reference"
    TRAIN_FEDERATED = "train_federated"
    VERIFY_ANCHOR = "verify_anchor"


class SplitId(StrEnum):
    BENIGN_TRAINING = "benign_training"
    BENIGN_CALIBRATION = "benign_calibration"
    HELD_OUT_EVALUATION = "held_out_evaluation"
    HISTORICAL_BENIGN_CALIBRATION = "historical_benign_calibration"
    FUTURE_BENIGN_RECALIBRATION = "future_benign_recalibration"
    FUTURE_HELD_OUT_EVALUATION = "future_held_out_evaluation"


class TemporalState(StrEnum):
    STATIC_REFERENCE = "static_reference"
    FROZEN_FUTURE = "frozen_future"
    ONE_SHOT_RECALIBRATED_FUTURE = "one_shot_recalibrated_future"


class SerializationFormat(StrEnum):
    PYDANTIC_JSON = "pydantic_json"
    PARQUET = "parquet"
    SAFETENSORS = "safetensors"
    SKOPS = "skops"


class WarningCode(StrEnum):
    NEAR_ZERO_MEAN_FPR = "near_zero_mean_fpr"
    UNDEFINED_COEFFICIENT_OF_VARIATION = "undefined_coefficient_of_variation"
    UNAVAILABLE_ATTACK_ASSIGNMENT = "unavailable_attack_assignment"
    INVALID_TEMPORAL_CHRONOLOGY = "invalid_temporal_chronology"
    UNRESOLVED_CLUSTER_ASSIGNMENTS = "unresolved_cluster_assignments"
    MISSING_TRAFFIC_RATE_EVIDENCE = "missing_traffic_rate_evidence"
    SERIALIZED_MESSAGE_SIZE_ESTIMATE = "serialized_message_size_estimate"


class TrafficRateEvidenceType(StrEnum):
    MEASURED = "measured"
    DATASET_DERIVED = "dataset_derived"
    EXTERNALLY_CITED = "externally_cited"
    UNAVAILABLE = "unavailable"


class CheckpointStatus(StrEnum):
    HISTORICAL_ENDPOINT = "historical_endpoint"
    CANDIDATE = "candidate"
    SELECTED_BY_NON_TEST_RULE = "selected_by_non_test_rule"
    STABILITY_EVIDENCE = "stability_evidence"


class CompletionStatus(StrEnum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"


class PreprocessingFitScope(StrEnum):
    CLIENT_LOCAL_TRAINING = "client_local_training"
    POOLED_TRAINING = "pooled_training"


class ProcessedDataBranch(StrEnum):
    FEDERATED = "federated"
    CENTRALIZED_REFERENCE = "centralized_reference"


class ReusableDataCoordinateKind(StrEnum):
    CANONICAL = "canonical"
    PROCESSED = "processed"
    RAW = "raw"


class RawDatasetDirectory(StrEnum):
    """On-disk directory names under data/raw/ for each audited corpus."""

    NBAIOT = "N-BaIoT"
    CICIOT2023 = "CIC_IOT_Dataset2023"
    EDGE_IIOTSET = "Edge-IIoTset"


class PartitionRole(StrEnum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    EVALUATION = "evaluation"
    FUTURE_RECALIBRATION = "future_recalibration"


class SplitProtocolId(StrEnum):
    NON_TEMPORAL_EQUAL_THIRDS = "non_temporal_equal_thirds"
    TEMPORAL_HISTORICAL_FUTURE = "temporal_historical_future"


class PreprocessingProtocolId(StrEnum):
    """Descriptive preprocessing protocol path identities."""

    FEDERATED_POOLED_MIN_MAX = "federated_pooled_min_max"
    FEDERATED_CLIENT_LOCAL_STANDARD = "federated_client_local_standard"
    CENTRALIZED_POOLED_MIN_MAX = "centralized_pooled_min_max"
    TEST_COLUMN_ORDER_PROJECTION = "test_column_order_projection"


class TrustedEstimatorClassName(StrEnum):
    STANDARD_SCALER = "standard_scaler"
    MIN_MAX_SCALER = "min_max_scaler"


class TrustedEstimatorModule(StrEnum):
    SKLEARN_PREPROCESSING = "sklearn_preprocessing"


class PreprocessExecutionStatus(StrEnum):
    BLOCKED_SCIENTIFIC_VALUE = "blocked_scientific_value"
    BLOCKED_POPULATION_CONSTRUCTION = "blocked_population_construction"
    PUBLISHED = "published"
    REUSED = "reused"
