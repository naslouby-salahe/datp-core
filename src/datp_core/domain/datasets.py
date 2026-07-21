"""Pure resolved dataset records used outside the configuration boundary."""

from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import cast

from attrs import define, field

from datp_core.domain.identifiers import DatasetId, DatasetSetupId, EligibilityPolicyId, MaterializationId
from datp_core.domain.values import (
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

    method: str
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
    normalization_strategy: str
    normalization_scope: str
    vocabulary_fit_split: str | None
    preprocessing_sequence: tuple[str, ...]
    row_exclusion: Mapping[str, str | bool] = field(converter=_as_mapping_str_str_or_bool)
    split_row_semantics: Mapping[str, str | bool] | None
    infeasibility_policy: str | None
    split_method: str
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
