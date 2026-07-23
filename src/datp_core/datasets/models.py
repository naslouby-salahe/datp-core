"""Pure resolved dataset records, and immutable row-level split manifests with their validation rules."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, StrEnum
from pathlib import Path
from typing import cast

from attrs import define, field

from datp_core.pipeline.identifiers import (
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    MaterializationId,
    NormalizationStrategyId,
)
from datp_core.pipeline.values import (
    FrozenJson,
    PositiveInt,
    Probability,
    RelativePath,
    Seed,
    as_frozen_json_mapping,
    as_int_mapping,
    as_optional_frozen_json_mapping,
    as_optional_int_mapping,
    as_optional_str_mapping,
    as_str_mapping,
    deep_freeze,
)


class AdapterKind(Enum):
    NBAIOT = "nbaiot"
    CICIOT2023 = "ciciot2023"
    EDGE_IIOTSET = "edge_iiotset"


class SplitMethod(StrEnum):
    RANDOM_FRACTIONAL = "random_fractional"
    CHRONOLOGICAL_GAPPED = "chronological_gapped"
    WITHIN_CLIENT_CHRONOLOGICAL = "within_client_chronological"


class ClientConstructionMethod(StrEnum):
    DATASET_FILE_PSEUDO_CLIENTS = "dataset_file_pseudo_clients"
    DIRICHLET_PARTITIONED_CLIENTS = "dirichlet_partitioned_clients"
    PHYSICAL_DEVICE_CLIENTS = "physical_device_clients"
    SENSOR_GROUP_CLIENTS = "sensor_group_clients"


class NormalizationStrategy(StrEnum):
    MIN_MAX = "min_max"
    STANDARD = "standard"


class NormalizationFitScope(StrEnum):
    GLOBAL_TRAIN = "global_train"
    PER_CLIENT_TRAIN = "per_client_train"
    HISTORICAL_TRAIN = "historical_train"


@define(frozen=True, slots=True, kw_only=True)
class EligibilityFallbackRecord:
    """Pure resolved deployment fallback for ineligible clients."""

    threshold_source: str
    shared_construction: str
    reported_status: str
    enters_primary_dispersion: bool


@define(frozen=True, slots=True, kw_only=True)
class EligibilityPolicyRecord:
    """Pure resolved client eligibility policy (per-dataset; distinct from a catalogue-level gate)."""

    identifier: EligibilityPolicyId
    minimum_benign_calibration_count: PositiveInt
    determined_before_test_evaluation: bool
    identical_across_policies_in_one_comparison: bool
    fpr_evaluable_requires_non_empty_benign_test_denominator: bool
    attack_evaluable_requires: tuple[str, ...]
    ineligible_clients_excluded_from_primary_dispersion: bool
    ineligible_client_deployment_fallback: EligibilityFallbackRecord
    zero_eligible_clients_behavior: str
    affects_standard_eligibility_minimum: bool | None
    permitted_use: str | None


@define(frozen=True, slots=True, kw_only=True)
class NormalizationStrategyRecord:
    """Pure resolved normalization strategy, referenced by DatasetMaterialization.normalization_strategy."""

    identifier: NormalizationStrategyId
    formula: str
    fitted_statistics: tuple[str, ...]
    constant_feature_rule: str
    out_of_range_transform_values: str
    fit_population: str
    standard_deviation_ddof: int | None


@define(frozen=True, slots=True, kw_only=True)
class ResolvedDatasetPaths:
    raw_data_root: Path
    raw_root: Path
    processed_root: Path


@define(frozen=True, slots=True, kw_only=True)
class SourceLayout:
    root: RelativePath
    ignored_suffixes: tuple[str, ...]
    ignored_subtrees: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ConfiguredSourceTree:
    """One read-only configured source tree and its schema expectation."""

    identifier: str
    root: RelativePath
    file_pattern: str
    expected_column_count: int
    executable: bool
    required_headers: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class DatasetInspectionContract:
    """Pure resolved source-integrity rules required before materialization."""

    source_trees: tuple[ConfiguredSourceTree, ...]
    require_identical_headers: bool
    device_directories: tuple[str, ...]
    benign_filename: str | None
    benign_file_required_per_device: bool
    attack_family_directories: tuple[str, ...]
    attack_family_required_per_device: bool
    normal_group_directories: tuple[str, ...]
    attack_filenames: tuple[str, ...]
    ignored_root_entries: tuple[str, ...]
    benign_label: str | None
    normal_traffic_root: RelativePath | None
    attack_traffic_root: RelativePath | None
    binary_label_header: str | None


def _as_mapping_str_str_or_bool(value: object) -> Mapping[str, str | bool]:
    return cast("Mapping[str, str | bool]", deep_freeze(value))


@define(frozen=True, slots=True, kw_only=True)
class SetupClientConstructionRecord:
    """Pure resolved per-setup client-construction contract (partitioning/allocation procedure)."""

    method: ClientConstructionMethod
    client_source: str | tuple[str, ...] | None
    client_semantics: str | None
    excluded_client_folders: tuple[str, ...] | None
    client_count: PositiveInt | None
    partition_condition: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    source_mixture_components: str | None
    label_field: str | None
    partition_seed: Seed | None
    partition_axes: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    allocation_procedure: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    same_proportions_govern: tuple[str, ...] | None
    split_role_preservation: str | None
    attack_row_assignment: str | None
    attack_labels_used_in_partition_generation: bool | None
    minimum_row_counts: Mapping[str, int] | None = field(converter=as_optional_int_mapping)
    retry_policy: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    feasibility_failure: str | None
    manifest_invariants: tuple[str, ...] | None
    manifest_fields: tuple[str, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class PartitionSeedContract:
    """Resolved deterministic seed derivation contract for synthetic client allocation."""

    key: str
    digest_bytes: PositiveInt


@define(frozen=True, slots=True, kw_only=True)
class DatasetSetup:
    identifier: DatasetSetupId
    materialization_id: MaterializationId
    capabilities: tuple[str, ...]  # authored `provides_capabilities`
    client_construction: SetupClientConstructionRecord
    validation_scope: str | None
    eligibility_gate: str | None
    client_population_must_equal_setup: DatasetSetupId | None


@define(frozen=True, slots=True, kw_only=True)
class DatasetMaterialization:
    identifier: MaterializationId
    role: str | None
    normalization_strategy: NormalizationStrategy
    normalization_scope: NormalizationFitScope
    vocabulary_fit_split: str | None
    preprocessing_sequence: tuple[str, ...]
    row_exclusion: Mapping[str, str | bool] = field(converter=_as_mapping_str_str_or_bool)
    split_row_semantics: Mapping[str, str | bool] | None
    infeasibility_policy: str | None
    split_method: SplitMethod
    split_seed: Seed | None
    split_ratios: tuple[tuple[str, Probability], ...]
    chronological_ratios: tuple[tuple[str, Probability], ...]
    split_ordering_basis: str | None
    split_ordering_scope: str | None
    split_gap_handling: str | None
    split_attack_rows: str | None
    split_attack_test_membership: str | None
    split_attack_ordering: str | None
    split_benign_attack_deduplication: str | None
    split_role_order: tuple[str, ...] | None
    split_excluded_client_folders: tuple[str, ...] | None
    split_exclusion_reason: str | None
    split_ordering_field: str | None
    split_ordering_sort: str | None
    split_rollover_policy: str | None
    split_rollover_scope: str | None
    split_boundary_rule: str | None
    split_boundary_index_formula: str | None
    split_future_leakage_check: str | None
    split_minimum_row_counts: Mapping[str, int] | None = field(converter=as_optional_int_mapping)
    split_missing_client_policy: str | None
    split_chronology_unverifiable_policy: str | None

    def ratio(self, role: str) -> Probability:
        for configured_role, configured_ratio in self.split_ratios:
            if configured_role == role:
                return configured_ratio
        raise KeyError(f"Materialization '{self.identifier.value}' has no configured ratio for '{role}'")

    def chronological_ratio(self, role: str) -> Probability:
        for configured_role, configured_ratio in self.chronological_ratios:
            if configured_role == role:
                return configured_ratio
        raise KeyError(f"Materialization '{self.identifier.value}' has no chronological ratio for '{role}'")


@define(frozen=True, slots=True, kw_only=True)
class DatasetSourceRecord:
    """One entry of a multi-source dataset's `source_layout.sources` mapping."""

    role: str
    root: RelativePath
    file_pattern: str
    owns: tuple[str, ...] | None
    permitted_uses: tuple[str, ...] | None
    contributes_rows_to_executable_materializations: bool | None
    defines_pseudo_clients: bool | None


@define(frozen=True, slots=True, kw_only=True)
class CrossSourceRelationshipRecord:
    row_count_equality_required: bool
    row_level_one_to_one_equivalence_assumed: bool
    join_by_row_position: str
    join_by_any_key: str


@define(frozen=True, slots=True, kw_only=True)
class DatasetSourceLayoutContractRecord:
    """Full authored `source_layout` contract (superset of the narrower `SourceLayout` used for audit)."""

    root: RelativePath
    benign_file: str | None
    benign_file_pattern: str | None
    normal_file_pattern: str | None
    attack_file_pattern: str | None
    device_dirs: tuple[str, ...] | None
    normal_group_folders: tuple[str, ...] | None
    executable_group_folders: tuple[str, ...] | None
    attack_files: tuple[str, ...] | None
    ignored_source_suffixes: tuple[str, ...]
    ignored_root_entries: tuple[str, ...]
    ignored_subtrees: tuple[str, ...]
    sources: Mapping[str, DatasetSourceRecord] | None
    executable_source: str | None
    cross_source_relationship: CrossSourceRelationshipRecord | None
    normal_traffic_root: RelativePath | None
    attack_traffic_root: RelativePath | None
    benign_file_required_per_device: bool | None
    attack_family_dirs: tuple[str, ...] | None
    attack_family_required_per_device: bool | None


@define(frozen=True, slots=True, kw_only=True)
class MulticlassLabelRecord:
    column: str
    type: str | None
    case: str | None


@define(frozen=True, slots=True, kw_only=True)
class LabelFieldsRecord:
    binary_label: Mapping[str, FrozenJson] = field(converter=as_frozen_json_mapping)
    multiclass_label: MulticlassLabelRecord | None
    benign_value: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    attack_class_mapping: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    device_family_mapping: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    family_taxonomy: str | None
    family_map: Mapping[str, str] | None = field(converter=as_optional_str_mapping)


@define(frozen=True, slots=True, kw_only=True)
class IdentitySchemeRecord:
    row_identity: Mapping[str, FrozenJson] = field(converter=as_frozen_json_mapping)
    client_identity: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    benign_group_identity: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    attack_row_group_identity: str | None
    label_identity: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    attack_family_identity: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    attack_type_identity: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    device_identity: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    device_mac_ip_field: str | None
    timestamp_field: str | Mapping[str, FrozenJson] = field(
        converter=lambda v: v if isinstance(v, str) else as_frozen_json_mapping(v)
    )
    chronological_ordering_basis: str | None
    provenance_fields: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class EndpointIdentityRecord:
    resolution: str
    fields: tuple[str, ...]
    internal_prefix: str
    subnet_component: str
    subnet_role_source: str
    subnet_to_group: Mapping[str, str] = field(
        converter=lambda v: as_str_mapping({str(k): item for k, item in cast("dict[int, str]", v).items()})
    )
    excluded_endpoints: Mapping[str, FrozenJson] = field(converter=as_frozen_json_mapping)
    direction_normalization: str
    use: str
    unresolved_row_policy: str


@define(frozen=True, slots=True, kw_only=True)
class RetainedNumericFeaturesRecord:
    role: str
    order: tuple[str, ...]
    numeric_parsing: Mapping[str, FrozenJson] = field(converter=as_frozen_json_mapping)
    on_invalid_value: str


@define(frozen=True, slots=True, kw_only=True)
class CategoricalEncodingRecord:
    strategy: str
    columns: tuple[str, ...]
    vocabulary_scope: str
    vocabulary_artifact: str
    vocabulary_fingerprint: str
    category_order: str
    encoded_feature_naming: str
    missing_category_policy: str
    unknown_category_policy: str
    unknown_indicator_distinct_from_missing_indicator: bool
    feature_order: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ModelFeaturesRecord:
    role: str
    type: str
    order: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class DatasetFieldSchemaRecord:
    """Full authored `field_schema` contract."""

    source_column_count: int | Mapping[str, int] = field(
        converter=lambda v: v if isinstance(v, int) else as_int_mapping(v)
    )
    header_required: bool
    header_must_be_identical_across_all_source_files: bool | None
    header_must_be_identical_across_all_files_in_a_tree: bool | None
    merged_header_extends_per_class_header_with: str | None
    label_column_position: str | None
    identity_scheme: IdentitySchemeRecord
    label_fields: LabelFieldsRecord
    model_features: ModelFeaturesRecord | None
    source_columns: tuple[str, ...] | None
    endpoint_identity: EndpointIdentityRecord | None
    attack_row_group_policy: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    retained_numeric_features: RetainedNumericFeaturesRecord | None
    post_encoding_feature_order: str | None
    categorical_encoding: str | CategoricalEncodingRecord
    leakage_exclusions: tuple[str, ...] | Mapping[str, FrozenJson] = field(
        converter=lambda v: as_frozen_json_mapping(v) if isinstance(v, Mapping) else tuple(cast("list[str]", v))
    )


@define(frozen=True, slots=True, kw_only=True)
class SourceContractRecord:
    """Full authored `source_contract` (row/schema integrity rules beyond `DatasetInspectionContract`)."""

    every_model_feature_present_in_merged_header: bool | None
    every_model_feature_present_in_every_file: bool | None
    model_feature_count_equals_source_column_count: bool | None
    per_class_schema_reference_check: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    malformed_row: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    empty_label_row: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    reject_unparseable_numeric_model_feature: bool | None
    reject_row_with_field_count_other_than_header: bool | None
    column_role_partition: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)
    positional_contract: Mapping[str, bool] | None = field(
        converter=lambda v: cast("Mapping[str, bool] | None", deep_freeze(v)) if v is not None else None
    )
    row_integrity_exclusions: Mapping[str, FrozenJson] | None = field(converter=as_optional_frozen_json_mapping)


@define(frozen=True, slots=True, kw_only=True)
class ResolvedDataset:
    dataset_id: DatasetId
    adapter_kind: AdapterKind
    display_name: str
    schema_id: str
    source_layout: SourceLayout
    source_layout_contract: DatasetSourceLayoutContractRecord
    field_schema: DatasetFieldSchemaRecord
    source_contract: SourceContractRecord
    client_identity_contract: Mapping[str, FrozenJson] | None
    inspection_contract: DatasetInspectionContract
    setups: tuple[DatasetSetup, ...]
    materializations: tuple[DatasetMaterialization, ...]
    eligibility_policy_id: EligibilityPolicyId
    capabilities: tuple[str, ...]
    paths: ResolvedDatasetPaths
    fingerprint_source_fields: tuple[str, ...]
    fingerprint_schema_fields: tuple[str, ...]
    fingerprint_materialization_fields: tuple[str, ...]
    fingerprint_client_assignment_fields: tuple[str, ...]

    def setup(self, identifier: DatasetSetupId) -> DatasetSetup:
        for setup in self.setups:
            if setup.identifier == identifier:
                return setup
        raise KeyError(f"Dataset setup not registered: {identifier}")


# --- split manifests (from domain/splits.py) ----------------------------------------------------


class SplitMembership(Enum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    TEST = "test"
    RECALIBRATION_REFERENCE = "recalibration_reference"
    HISTORICAL_TRAINING = "historical_training"
    HISTORICAL_CALIBRATION = "historical_calibration"
    FUTURE_RECALIBRATION = "future_recalibration"
    FUTURE_EVALUATION = "future_evaluation"


@dataclass(frozen=True, slots=True, kw_only=True)
class MaterializedSplitEvidence:
    """Observed schema and immutable row allocation extracted from one payload."""

    manifest: SplitManifest
    schema_columns: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not self.schema_columns:
            raise ValueError("Materialized split evidence requires a non-empty schema")


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitManifestEntry:
    source_path: str
    source_row_index: int
    client_id: str
    membership: SplitMembership
    is_attack: bool
    chronology_key: int | None = None

    def __post_init__(self) -> None:
        if not self.source_path:
            raise ValueError("A split manifest entry requires a source path")
        if self.source_row_index < 1:
            raise ValueError("A split manifest row index must be positive")
        if not self.client_id:
            raise ValueError("A split manifest entry requires a client identifier")

    @property
    def row_identity(self) -> tuple[str, int]:
        return self.source_path, self.source_row_index


@dataclass(frozen=True, slots=True, kw_only=True)
class SplitManifest:
    entries: tuple[SplitManifestEntry, ...]
    minimum_benign_calibration_count: int

    def __post_init__(self) -> None:
        if not self.entries:
            raise ValueError("A split manifest cannot be empty")
        if self.minimum_benign_calibration_count < 1:
            raise ValueError("minimum_benign_calibration_count must be positive")
        if len({entry.row_identity for entry in self.entries}) != len(self.entries):
            raise ValueError("A source row may appear in only one split-manifest entry")
        memberships = {entry.membership for entry in self.entries}
        if memberships <= _STANDARD_MEMBERSHIPS:
            _validate_standard_manifest(self.entries, memberships)
        elif memberships <= _STATIC_REFERENCE_MEMBERSHIPS:
            _validate_static_reference_manifest(self.entries, memberships)
        elif memberships <= _TEMPORAL_MEMBERSHIPS:
            _validate_temporal_manifest(self.entries, memberships)
        else:
            raise ValueError("A split manifest cannot mix standard and temporal memberships")

    @property
    def client_ids(self) -> tuple[str, ...]:
        return tuple(sorted({entry.client_id for entry in self.entries}))

    @property
    def eligible_client_ids(self) -> tuple[str, ...]:
        counts = Counter(
            entry.client_id
            for entry in self.entries
            if entry.membership in {SplitMembership.CALIBRATION, SplitMembership.HISTORICAL_CALIBRATION}
            and not entry.is_attack
        )
        return tuple(
            sorted(
                client_id for client_id in self.client_ids if counts[client_id] >= self.minimum_benign_calibration_count
            )
        )

    @property
    def ineligible_client_ids(self) -> tuple[str, ...]:
        eligible = set(self.eligible_client_ids)
        return tuple(client_id for client_id in self.client_ids if client_id not in eligible)

    @property
    def split_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(entry.membership.value for entry in self.entries).items()))

    @property
    def class_counts(self) -> dict[str, int]:
        return {
            "benign": sum(not entry.is_attack for entry in self.entries),
            "attack": sum(entry.is_attack for entry in self.entries),
        }

    @property
    def client_row_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(entry.client_id for entry in self.entries).items()))


_STANDARD_MEMBERSHIPS = {SplitMembership.TRAIN, SplitMembership.CALIBRATION, SplitMembership.TEST}
_STATIC_REFERENCE_MEMBERSHIPS = {
    SplitMembership.TRAIN,
    SplitMembership.CALIBRATION,
    SplitMembership.RECALIBRATION_REFERENCE,
    SplitMembership.TEST,
}
_TEMPORAL_MEMBERSHIPS = {
    SplitMembership.HISTORICAL_TRAINING,
    SplitMembership.HISTORICAL_CALIBRATION,
    SplitMembership.FUTURE_RECALIBRATION,
    SplitMembership.FUTURE_EVALUATION,
}


def _validate_standard_manifest(entries: tuple[SplitManifestEntry, ...], memberships: set[SplitMembership]) -> None:
    if memberships != _STANDARD_MEMBERSHIPS:
        raise ValueError("A standard split manifest requires train, calibration, and test memberships")
    if any(entry.is_attack and entry.membership is not SplitMembership.TEST for entry in entries):
        raise ValueError("Attack rows may not enter standard training or calibration memberships")
    _validate_client_support(entries, SplitMembership.TRAIN, SplitMembership.CALIBRATION)


def _validate_static_reference_manifest(
    entries: tuple[SplitManifestEntry, ...], memberships: set[SplitMembership]
) -> None:
    if memberships != _STATIC_REFERENCE_MEMBERSHIPS:
        raise ValueError("A static-reference split manifest requires all four configured memberships")
    if any(entry.is_attack for entry in entries):
        raise ValueError("Static-reference Edge rows must remain benign and unassigned to attack clients")
    _validate_client_support(entries, SplitMembership.TRAIN, SplitMembership.CALIBRATION)


def _validate_temporal_manifest(entries: tuple[SplitManifestEntry, ...], memberships: set[SplitMembership]) -> None:
    if memberships != _TEMPORAL_MEMBERSHIPS:
        raise ValueError("A temporal split manifest requires all four chronological memberships")
    if any(entry.chronology_key is None for entry in entries):
        raise ValueError("Temporal split manifests require a chronology key for every row")
    if any(
        entry.is_attack
        and entry.membership in {SplitMembership.HISTORICAL_TRAINING, SplitMembership.HISTORICAL_CALIBRATION}
        for entry in entries
    ):
        raise ValueError("Attack rows may not enter temporal training or calibration memberships")
    _validate_client_support(entries, SplitMembership.HISTORICAL_TRAINING, SplitMembership.HISTORICAL_CALIBRATION)
    order = {membership: index for index, membership in enumerate(SplitMembership)}
    for client_id in {entry.client_id for entry in entries}:
        client_entries = sorted(
            (entry for entry in entries if entry.client_id == client_id), key=lambda entry: entry.chronology_key or 0
        )
        memberships_in_order = [order[entry.membership] for entry in client_entries]
        if memberships_in_order != sorted(memberships_in_order):
            raise ValueError(f"Temporal split manifest has future leakage for client '{client_id}'")


def _validate_client_support(
    entries: tuple[SplitManifestEntry, ...],
    training_membership: SplitMembership,
    calibration_membership: SplitMembership,
) -> None:
    clients = {entry.client_id for entry in entries}
    for client_id in clients:
        client_memberships = {entry.membership for entry in entries if entry.client_id == client_id}
        if training_membership not in client_memberships or calibration_membership not in client_memberships:
            raise ValueError(f"Client '{client_id}' lacks required training or calibration membership")
