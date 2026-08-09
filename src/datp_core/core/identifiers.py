"""Closed DATP-Core identities and validated string identifiers."""

from dataclasses import dataclass
from enum import StrEnum
from typing import ClassVar

from datp_core.core.contracts import (
    pydantic_value_schema,
    sequence_pydantic_schema,
    str_subclass_schema,
    validate_non_empty_tuple,
    validate_unique,
)


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


class ExperimentReadiness(StrEnum):
    DECLARED = "declared"
    EXECUTABLE = "executable"
    SUPPRESSED = "suppressed"
    INFEASIBLE = "infeasible"
    BLOCKED = "blocked"


class ProgrammeStatus(StrEnum):
    NOT_STARTED = "not_started"
    DATASET_READY = "dataset_ready"
    PREPARATION_READY = "preparation_ready"
    BLOCKED_BY_DEPENDENCY = "blocked_by_dependency"
    BLOCKED_BY_ANCHOR = "blocked_by_anchor"
    RUNNING = "running"
    INCOMPLETE = "incomplete"
    INVALID = "invalid"
    EXECUTION_COMPLETE = "execution_complete"
    ANALYSIS_COMPLETE = "analysis_complete"
    REPORT_READY = "report_ready"
    REPORT_GENERATED = "report_generated"


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
    FPR_EVALUABLE = "fpr_evaluable"
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
    COMMUNICATION_BYTES = "communication_bytes"
    ALERTS_PER_DAY = "alerts_per_day"
    RECONSTRUCTION_ERROR = "reconstruction_error"
    EMPIRICAL_CUMULATIVE_PROBABILITY = "empirical_cumulative_probability"
    JAIN_FAIRNESS_INDEX = "jain_fairness_index"
    GINI_COEFFICIENT = "gini_coefficient"


class AvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNDEFINED = "undefined"
    SUPPRESSED = "suppressed"
    INFEASIBLE = "infeasible"


class ThresholdMethodExecutionStatus(StrEnum):
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    INFEASIBLE = "infeasible"
    FAILED = "failed"


class PublicationStatus(StrEnum):
    PUBLISHED = "published"
    REUSED = "reused"


class StageOperationId(StrEnum):
    ANALYZE = "analyze"
    CALIBRATE = "calibrate"
    CONSTRUCT_CENTRALIZED_REFERENCE_THRESHOLD = "construct_centralized_reference_threshold"
    CONSTRUCT_FEDERATED_THRESHOLDS = "construct_federated_thresholds"
    CONSTRUCT_POPULATION = "construct_population"
    EVALUATE_CENTRALIZED_REFERENCE = "evaluate_centralized_reference"
    EVALUATE_FEDERATED = "evaluate_federated"
    MATERIALIZE = "materialize"
    PREPROCESS_CENTRALIZED_REFERENCE = "preprocess_centralized_reference"
    PREPROCESS_FEDERATED = "preprocess_federated"
    SCORE_CENTRALIZED_REFERENCE = "score_centralized_reference"
    SCORE_FEDERATED = "score_federated"
    SELECT_CENTRALIZED_REFERENCE_CHECKPOINT = "select_centralized_reference_checkpoint"
    SELECT_FEDERATED_CHECKPOINT = "select_federated_checkpoint"
    SPLIT = "split"
    TRAIN_CENTRALIZED_REFERENCE = "train_centralized_reference"
    TRAIN_FEDERATED = "train_federated"
    VERIFY_ANCHOR = "verify_anchor"


class TemporalState(StrEnum):
    STATIC_REFERENCE = "static_reference"
    FROZEN_FUTURE = "frozen_future"
    RECALIBRATED_FUTURE = "recalibrated_future"


class SerializationFormat(StrEnum):
    PYDANTIC_JSON = "pydantic_json"
    PARQUET = "parquet"
    SAFETENSORS = "safetensors"
    SKOPS = "skops"


class CommunicationEstimationMethod(StrEnum):
    SERIALIZED_MESSAGE_SIZE_ESTIMATE = "serialized_message_size_estimate"
    MEASURED_NETWORK_TRAFFIC = "measured_network_traffic"


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


class CheckpointSelectionRule(StrEnum):
    FIXED_TERMINAL_MAXIMUM_ROUND = "fixed_terminal_maximum_round"


class FedProxCoefficientSelectionRule(StrEnum):
    FEDPROX_MINIMUM_TERMINAL_TRAINING_LOSS = "fedprox_minimum_terminal_training_loss"


class FedProxRoleDirectory(StrEnum):
    PRIMARY = "primary"
    SENSITIVITY = "sensitivity"


class ProcessedDataBranch(StrEnum):
    FEDERATED = "federated"
    CENTRALIZED_REFERENCE = "centralized_reference"


class ReusableDataCoordinateKind(StrEnum):
    CANONICAL = "canonical"
    PROCESSED = "processed"
    RAW = "raw"


class RawDatasetDirectory(StrEnum):
    NBAIOT = "N-BaIoT"
    CICIOT2023 = "CIC_IOT_Dataset2023"
    EDGE_IIOTSET = "Edge-IIoTset"


class PartitionRole(StrEnum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    EVALUATION = "evaluation"
    FUTURE_RECALIBRATION = "future_recalibration"
    STATIC_REFERENCE_RESERVE = "static_reference_reserve"


class SplitProtocolId(StrEnum):
    NON_TEMPORAL_EQUAL_THIRDS = "non_temporal_equal_thirds"
    TEMPORAL_HISTORICAL_FUTURE = "temporal_historical_future"
    RANDOM_FRACTIONAL_STATIC_REFERENCE = "random_fractional_static_reference"


class PreprocessingProtocolId(StrEnum):
    FEDERATED_POOLED_MIN_MAX = "federated_pooled_min_max"
    FEDERATED_CLIENT_LOCAL_STANDARD = "federated_client_local_standard"
    CENTRALIZED_POOLED_MIN_MAX = "centralized_pooled_min_max"
    TEST_COLUMN_ORDER_PROJECTION = "test_column_order_projection"


class ContractSubject(StrEnum):
    ARTIFACT_PATH = "artifact_path"
    ATTACK_LABELS = "attack_labels"
    AUTOENCODER = "autoencoder"
    BATCH_SIZE = "batch_size"
    CALIBRATION = "calibration"
    CANDIDATES = "candidates"
    CHECKPOINT_CANDIDATES = "checkpoint_candidates"
    CHECKPOINT_SELECTION_RULE = "checkpoint_selection_rule"
    CLIENT = "client"
    CLIENT_IDENTITY = "client_identity"
    CONFIRMATORY_LADDER = "confirmatory_ladder"
    COORDINATE = "coordinate"
    CUDA = "cuda"
    FEATURES = "features"
    FEDPROX_COEFFICIENT_SELECTION_RULE = "fedprox_coefficient_selection_rule"
    HELD_OUT_METRICS = "held_out_metrics"
    LABEL = "label"
    LOCAL_QUANTILE_MEAN = "local_quantile_mean"
    METRICS = "metrics"
    OPTIMIZER = "optimizer"
    PREPROCESSING = "preprocessing"
    QUANTILE = "quantile"
    RECONSTRUCTION_ERROR = "reconstruction_error"
    ROWS = "rows"
    RUNTIME = "runtime"
    SCHEMA = "schema"
    SCORES = "scores"
    SEED = "seed"
    SPLIT = "split"
    THRESHOLD = "threshold"
    THRESHOLD_IDENTITY = "threshold_identity"
    THRESHOLD_METHOD = "threshold_method"
    TRAFFIC_RATE = "traffic_rate"
    TRAINING = "training"
    TRAINING_HYPERPARAMETERS = "training_hyperparameters"
    WIDTHS = "widths"


class TrainingHistoryColumn(StrEnum):
    EPOCH = "epoch"
    MEAN_TRAINING_LOSS = "mean_training_loss"


class ScoreFrameColumn(StrEnum):
    STABLE_ROW_ID = "stable_row_id"
    OUTCOME_LABEL = "outcome_label"
    RECONSTRUCTION_ERROR = "reconstruction_error"


class QuantileInterpolationSemantics(StrEnum):
    NUMPY_QUANTILE_LINEAR = "numpy_quantile_linear"


class NonEmptyString(str):
    validation_name: ClassVar[str] = "value"

    def __new__(cls, value: str):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{cls.validation_name} must be a non-empty string")
        return super().__new__(cls, value)

    __get_pydantic_core_schema__ = classmethod(str_subclass_schema)


class FeatureName(NonEmptyString):
    validation_name: ClassVar[str] = "feature name"


class OutcomeLabel(NonEmptyString):
    validation_name: ClassVar[str] = "outcome label"


class StableRowId(NonEmptyString):
    validation_name: ClassVar[str] = "stable row ID"


class CaptureTimestampColumn(NonEmptyString):
    validation_name: ClassVar[str] = "capture timestamp column"


class SafeTensorFilename(NonEmptyString):
    validation_name: ClassVar[str] = "SafeTensors filename"

    def __new__(cls, value: str) -> "SafeTensorFilename":
        instance = super().__new__(cls, value)
        if not instance.endswith(".safetensors"):
            raise ValueError("SafeTensors filename must end with .safetensors")
        return instance


class ArtifactFileName(NonEmptyString):
    validation_name: ClassVar[str] = "artifact filename"


class SerializedDocumentText(NonEmptyString):
    validation_name: ClassVar[str] = "serialized document text"


class ValidationSubject(NonEmptyString):
    validation_name: ClassVar[str] = "validation subject"


class ValidationReasonText(NonEmptyString):
    validation_name: ClassVar[str] = "validation reason text"


class FeatureNamePrefix(NonEmptyString):
    validation_name: ClassVar[str] = "feature name prefix"


class SourcePathPart(NonEmptyString):
    validation_name: ClassVar[str] = "source path part"


class AttackSubtypeToken(NonEmptyString):
    validation_name: ClassVar[str] = "attack subtype token"


class RawSourceFilename(NonEmptyString):
    validation_name: ClassVar[str] = "raw source filename"


class GlobPattern(NonEmptyString):
    validation_name: ClassVar[str] = "glob pattern"


class ControlledPartitionPathSegment(NonEmptyString):
    validation_name: ClassVar[str] = "controlled partition path segment"


class RelatedPublicationMemberIdentity(NonEmptyString):
    validation_name: ClassVar[str] = "related publication member identity"


class ReloadValidationEvidence(NonEmptyString):
    validation_name: ClassVar[str] = "reload validation evidence"


class CudaDeviceName(NonEmptyString):
    validation_name: ClassVar[str] = "CUDA device name"


class CudaVersion(NonEmptyString):
    validation_name: ClassVar[str] = "CUDA version"


class TorchVersion(NonEmptyString):
    validation_name: ClassVar[str] = "PyTorch version"


class ColumnName(NonEmptyString):
    validation_name: ClassVar[str] = "column name"


class ValidationLabel(NonEmptyString):
    validation_name: ClassVar[str] = "validation label"


class PhysicalSchemaText(NonEmptyString):
    validation_name: ClassVar[str] = "physical schema text"


class SourceIdentity(NonEmptyString):
    validation_name: ClassVar[str] = "source identity"


class ChronologyGroupIdentity(NonEmptyString):
    validation_name: ClassVar[str] = "chronology group identity"


class ValidationSourceContext(NonEmptyString):
    validation_name: ClassVar[str] = "validation source context"


class CanonicalizationContractName(NonEmptyString):
    validation_name: ClassVar[str] = "canonicalization contract name"


class CanonicalSourcePath(NonEmptyString):
    validation_name: ClassVar[str] = "canonical source path"


class CanonicalAssetRoleToken(NonEmptyString):
    validation_name: ClassVar[str] = "canonical asset role token"


class EligibilityReasonToken(NonEmptyString):
    validation_name: ClassVar[str] = "eligibility reason token"


class DecisionRationale(NonEmptyString):
    validation_name: ClassVar[str] = "decision rationale"


class AnalysisReasonText(NonEmptyString):
    validation_name: ClassVar[str] = "analysis reason text"


class FigureLabel(NonEmptyString):
    validation_name: ClassVar[str] = "figure label"


class FigureTitle(NonEmptyString):
    validation_name: ClassVar[str] = "figure title"


class ClaimWording(NonEmptyString):
    validation_name: ClassVar[str] = "claim wording"


class NormalizedClaimWording(NonEmptyString):
    validation_name: ClassVar[str] = "normalized claim wording"


class ReportLine(str):
    """One rendered line of report output; may be blank for paragraph separation."""


class FileContentText(str):
    """Textual body of a file written to the artifact tree; allows empty content."""


class MessageEndpoint(NonEmptyString):
    validation_name: ClassVar[str] = "message endpoint"


class CommunicationGroupIdentity(NonEmptyString):
    validation_name: ClassVar[str] = "communication group identity"


class TrafficRateReference(NonEmptyString):
    validation_name: ClassVar[str] = "traffic-rate reference"


class TrafficRateProvenanceText(NonEmptyString):
    validation_name: ClassVar[str] = "traffic-rate provenance"


class TrafficRateLocatorText(NonEmptyString):
    validation_name: ClassVar[str] = "traffic-rate locator text"


class RegimeLabel(NonEmptyString):
    validation_name: ClassVar[str] = "regime label"


class StageExecutionEvidence(NonEmptyString):
    validation_name: ClassVar[str] = "stage execution evidence"


class UtcInstantText(NonEmptyString):
    validation_name: ClassVar[str] = "UTC instant text"


class ArtifactDirectoryPathText(NonEmptyString):
    validation_name: ClassVar[str] = "artifact directory path text"


class AnalysisMarkerText(NonEmptyString):
    validation_name: ClassVar[str] = "analysis marker text"


class SourceRuleDescription(NonEmptyString):
    validation_name: ClassVar[str] = "source-defined rule description"


class IntervalDescriptionText(NonEmptyString):
    validation_name: ClassVar[str] = "interval description text"


class ScoreArtifactPathText(NonEmptyString):
    validation_name: ClassVar[str] = "score artifact path text"


@dataclass(frozen=True, slots=True)
class ClientPathToken:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("client path token must be non-empty")
        if self.value in {".", ".."} or any(token in self.value for token in ("=", "/", "\\")):
            raise ValueError("client path token must be a single non-relative path segment without key=value syntax")

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)


@dataclass(frozen=True, slots=True)
class ClientIdentityToken:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("client identity token must be non-empty")

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)


@dataclass(frozen=True, slots=True)
class FamilyIdentity:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value:
            raise ValueError("family identity must be non-empty")

    __get_pydantic_core_schema__ = classmethod(pydantic_value_schema)


@dataclass(frozen=True, slots=True)
class FeatureNameSequence:
    names: tuple[FeatureName, ...]

    def __post_init__(self) -> None:
        wrapped = tuple(item if isinstance(item, FeatureName) else FeatureName(item) for item in self.names)
        object.__setattr__(self, "names", wrapped)
        validate_non_empty_tuple(self.names, "feature name sequence")
        validate_unique(self.names, "feature names")

    def __len__(self) -> int:
        return len(self.names)

    def __iter__(self):
        return iter(self.names)

    def as_list(self) -> list[FeatureName]:
        return list(self.names)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)


@dataclass(frozen=True, slots=True)
class OutcomeLabelSequence:
    labels: tuple[OutcomeLabel, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.labels, tuple):
            raise TypeError("outcome labels must be an immutable tuple")
        object.__setattr__(
            self,
            "labels",
            tuple(item if isinstance(item, OutcomeLabel) else OutcomeLabel(item) for item in self.labels),
        )

    def __len__(self) -> int:
        return len(self.labels)

    def __iter__(self):
        return iter(self.labels)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)


@dataclass(frozen=True, slots=True)
class StableRowIdSequence:
    row_ids: tuple[StableRowId, ...]

    def __post_init__(self) -> None:
        wrapped = tuple(item if isinstance(item, StableRowId) else StableRowId(item) for item in self.row_ids)
        object.__setattr__(self, "row_ids", wrapped)
        validate_non_empty_tuple(self.row_ids, "stable row ID sequence")
        validate_unique(self.row_ids, "stable row IDs")

    def __len__(self) -> int:
        return len(self.row_ids)

    def __iter__(self):
        return iter(self.row_ids)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)


class CoordinateStableKey(NonEmptyString):
    validation_name: ClassVar[str] = "coordinate stable key"


class MarkdownText(NonEmptyString):
    validation_name: ClassVar[str] = "markdown text"
