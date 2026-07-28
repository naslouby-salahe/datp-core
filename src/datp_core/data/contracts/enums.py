"""Closed data-package vocabularies."""

from __future__ import annotations

from enum import StrEnum


class AdapterKind(StrEnum):
    NBAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"


class DatasetPlanKind(StrEnum):
    CICIOT2023 = "ciciot2023"
    NBAIOT_PHYSICAL = "nbaiot_physical"
    NBAIOT_DIRICHLET = "nbaiot_dirichlet"
    EDGE_IIOTSET = "edge_iiotset"


class DatasetCapability(StrEnum):
    BENIGN_CALIBRATION = "benign_calibration"
    ATTACK_EVALUATION = "attack_evaluation"
    TEMPORAL_RECALIBRATION = "temporal_recalibration"
    PHYSICAL_CLIENT_IDENTITY = "physical_client_identity"
    PSEUDO_CLIENT_IDENTITY = "pseudo_client_identity"
    SYNTHETIC_CLIENT_PARTITION = "synthetic_client_partition"


class SourceTreeKind(StrEnum):
    MERGED = "merged"
    DEVICE_HIERARCHY = "device_hierarchy"
    BENIGN_GROUPS = "benign_groups"
    ATTACK_REFERENCE = "attack_reference"


class SourceRole(StrEnum):
    EXECUTABLE = "executable"
    AUDIT_ONLY = "audit_only"


class SourceDiscoveryMode(StrEnum):
    GLOB = "glob"
    RECURSIVE_GLOB = "recursive_glob"


class InvalidRowPolicy(StrEnum):
    EXCLUDE_ROW = "exclude_row"
    FAIL_SOURCE = "fail_source"


class CsvColumnKind(StrEnum):
    FLOAT64 = "float64"
    TEXT = "text"


class LabelCasePolicy(StrEnum):
    EXACT = "exact"
    CASEFOLD = "casefold"
    UPPER = "upper"
    LOWER = "lower"


class ClientIdentityMethod(StrEnum):
    FILE_NAME = "file_name"
    RELATIVE_PATH_COMPONENT = "relative_path_component"


class SplitMethod(StrEnum):
    RANDOM_FRACTIONAL = "random_fractional"
    CHRONOLOGICAL_GAPPED = "chronological_gapped"
    WITHIN_CLIENT_CHRONOLOGICAL = "within_client_chronological"


class SplitLayout(StrEnum):
    STANDARD = "standard"
    STATIC_RECALIBRATION_REFERENCE = "static_recalibration_reference"
    TEMPORAL = "temporal"


class SplitMembership(StrEnum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    TEST = "test"
    RECALIBRATION_REFERENCE = "recalibration_reference"
    HISTORICAL_TRAINING = "historical_training"
    HISTORICAL_CALIBRATION = "historical_calibration"
    FUTURE_RECALIBRATION = "future_recalibration"
    FUTURE_EVALUATION = "future_evaluation"


class AttackAssignment(StrEnum):
    TEST = "test"
    EXCLUDE = "exclude"


class DeduplicationPolicy(StrEnum):
    NONE = "none"
    EXACT_WITHIN_CLASS = "exact_within_class"
    EXACT_WITHIN_CLIENT = "exact_within_client"


class DeterministicOrdering(StrEnum):
    CONTENT_DIGEST = "content_digest"
    SOURCE_PROVENANCE = "source_provenance"


class GapHandling(StrEnum):
    EXCLUDE = "exclude"


class BoundaryRule(StrEnum):
    FLOOR = "floor"


class SortDirection(StrEnum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


class ChronologyRolloverPolicy(StrEnum):
    ADD_FIXED_PERIOD_ON_DECREASE = "add_fixed_period_on_decrease"
    FORBID_DECREASE = "forbid_decrease"


class ClientConstructionMethod(StrEnum):
    DATASET_FILE_PSEUDO_CLIENTS = "dataset_file_pseudo_clients"
    PHYSICAL_DEVICE_CLIENTS = "physical_device_clients"
    SENSOR_GROUP_CLIENTS = "sensor_group_clients"
    DIRICHLET_PARTITIONED_CLIENTS = "dirichlet_partitioned_clients"


class PartitionAllocation(StrEnum):
    DIRICHLET = "dirichlet"
    EQUAL_ACROSS_SOURCE_DOMAINS = "equal_across_source_domains"


class SyntheticClientNamingPolicy(StrEnum):
    PREFIXED_ZERO_PADDED_INDEX = "prefixed_zero_padded_index"


class NormalizationStrategy(StrEnum):
    MIN_MAX = "min_max"
    STANDARD = "standard"


class NormalizationFitScope(StrEnum):
    GLOBAL_TRAIN = "global_train"
    PER_CLIENT_TRAIN = "per_client_train"
    HISTORICAL_TRAIN = "historical_train"


class ConstantFeaturePolicy(StrEnum):
    ZERO = "zero"
    ERROR = "error"


class OutOfRangePolicy(StrEnum):
    PRESERVE = "preserve"
    CLIP = "clip"
    ERROR = "error"


class CategoricalEncodingStrategy(StrEnum):
    ONE_HOT = "one_hot"


class CategoryOrder(StrEnum):
    LEXICOGRAPHIC = "lexicographic"


class MissingCategoryPolicy(StrEnum):
    DEDICATED_INDICATOR = "dedicated_indicator"


class UnknownCategoryPolicy(StrEnum):
    DEDICATED_INDICATOR = "dedicated_indicator"


class EncodedFeatureNaming(StrEnum):
    COLUMN_EQUALS_CATEGORY = "column_equals_category"


class ParquetCompression(StrEnum):
    NONE = "none"
    SNAPPY = "snappy"
    GZIP = "gzip"
    BROTLI = "brotli"
    ZSTD = "zstd"
    LZ4 = "lz4"


class HashAlgorithm(StrEnum):
    BLAKE2B = "blake2b"
    SHA256 = "sha256"


class MaterializedColumn(StrEnum):
    SPLIT = "split"
    CLIENT_ID = "client_id"
    IS_ATTACK = "is_attack"
    MULTICLASS_LABEL = "multiclass_label"
    ATTACK_FAMILY = "attack_family"
    SOURCE_PATH = "source_path"
    SOURCE_ROW_INDEX = "source_row_index"
    CHRONOLOGY_KEY = "chronology_key"


class MaterializedArtifactShape(StrEnum):
    CICIOT2023 = "ciciot2023"
    NBAIOT = "nbaiot"
    EDGE_BENIGN_STATIC = "edge_benign_static"
    EDGE_BENIGN_TEMPORAL = "edge_benign_temporal"


class MaterializationArtifactKind(StrEnum):
    DATASET = "dataset"
    SPLIT_MANIFEST = "split_manifest"
    READINESS = "readiness"
    PREPROCESSING = "preprocessing"
    PARTITION_MANIFEST = "partition_manifest"


class StagingArtifactName(StrEnum):
    DATABASE = "materialization.duckdb"
    TEMPORARY_DIRECTORY = "duckdb-temp"
    RAW_PAYLOAD = "raw.parquet"
    ENCODED_PAYLOAD = "encoded.parquet"
    FINAL_PAYLOAD = "dataset.parquet"


class ArtifactSchemaVersion(StrEnum):
    MATERIALIZED_V1 = "materialized.v1"
    SPLIT_SUMMARY_V1 = "split-summary.v1"
    NORMALIZATION_V1 = "normalization.v1"
    CATEGORICAL_VOCABULARY_V1 = "categorical-vocabulary.v1"
    PARTITION_V1 = "partition.v1"
    READINESS_V1 = "readiness.v1"


class MaterializationStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INFEASIBLE = "infeasible"


class FeasibilityStatus(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"


class AuditSeverity(StrEnum):
    BLOCKING = "blocking"
    WARNING = "warning"


class AuditIssueCode(StrEnum):
    NO_SOURCE_FILES = "no_source_files"
    SOURCE_OUTSIDE_ROOT = "source_outside_root"
    SOURCE_HEADER_MISMATCH = "source_header_mismatch"
    AUDIT_SOURCE_MISSING = "audit_source_missing"
    MATERIALIZED_EMPTY = "materialized_empty"
    MATERIALIZED_SCHEMA_MISMATCH = "materialized_schema_mismatch"
    REQUIRED_SPLIT_MISSING = "required_split_missing"
    CLIENT_COUNT_MISMATCH = "client_count_mismatch"
    BENIGN_CALIBRATION_INSUFFICIENT = "benign_calibration_insufficient"
    ATTACK_CAPABILITY_MISMATCH = "attack_capability_mismatch"
    TEMPORAL_CAPABILITY_MISMATCH = "temporal_capability_mismatch"
    NON_FINITE_FEATURE = "non_finite_feature"
    CHRONOLOGY_ORDER_VIOLATION = "chronology_order_violation"


class ReadinessGateFailureCode(StrEnum):
    MINIMUM_ELIGIBLE_CLIENTS = "minimum_eligible_clients"
    MINIMUM_ELIGIBLE_PROPORTION = "minimum_eligible_proportion"
    REQUIRED_CAPABILITY_MISSING = "required_capability_missing"


class DataFailureCode(StrEnum):
    CONFIGURATION = "configuration"
    SOURCE_CONTAINMENT = "source_containment"
    SOURCE_HEADER = "source_header"
    SOURCE_ROW = "source_row"
    SOURCE_EMPTY = "source_empty"
    SOURCE_CHANGED = "source_changed"
    SPLIT = "split"
    PARTITION = "partition"
    NORMALIZATION = "normalization"
    ENCODING = "encoding"
    SCHEMA = "schema"
    READINESS = "readiness"
    ARTIFACT = "artifact"
