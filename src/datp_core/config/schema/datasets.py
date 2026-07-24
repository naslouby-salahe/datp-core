"""Strict Pydantic 2 models for authored dataset configuration documents (datasets/<name>.yaml)."""

from __future__ import annotations

from typing import Literal

from pydantic import ConfigDict, Field

from datp_core.config.schema import SchemaVersionOneConfigModel, StrictFrozenConfigModel


class DatasetSourceConfig(StrictFrozenConfigModel):
    role: Literal["executable", "reference_only"]
    root: str
    file_pattern: str
    owns: list[str] | None = None
    permitted_uses: list[str] | None = None
    contributes_rows_to_executable_materializations: bool | None = None
    defines_pseudo_clients: bool | None = None


class CrossSourceRelationshipConfig(StrictFrozenConfigModel):
    row_count_equality_required: bool
    row_level_one_to_one_equivalence_assumed: bool
    join_by_row_position: Literal["forbidden"]
    join_by_any_key: Literal["forbidden"]


class DatasetSourceLayoutConfig(StrictFrozenConfigModel):
    root: str
    benign_file: str | None = None
    benign_file_pattern: str | None = None
    normal_file_pattern: str | None = None
    attack_file_pattern: str | None = None
    device_dirs: list[str] | None = None
    normal_group_folders: list[str] | None = None
    executable_group_folders: list[str] | None = None
    attack_files: list[str] | None = None
    ignored_source_suffixes: list[str] = Field(default_factory=list)
    ignored_root_entries: list[str] = Field(default_factory=list)
    ignored_subtrees: list[str] = Field(default_factory=list)
    sources: dict[str, DatasetSourceConfig] | None = None
    executable_source: str | None = None
    cross_source_relationship: CrossSourceRelationshipConfig | None = None
    normal_traffic_root: str | None = None
    attack_traffic_root: str | None = None
    benign_file_required_per_device: bool | None = None
    attack_family_dirs: list[str] | None = None
    attack_family_required_per_device: bool | None = None


class IdentitySchemeConfig(StrictFrozenConfigModel):
    row_identity: dict[str, str | bool | list[str]]
    client_identity: dict[str, str | bool] | None = None
    benign_group_identity: dict[str, str] | None = None
    attack_row_group_identity: str | None = None
    label_identity: dict[str, str] | None = None
    attack_family_identity: dict[str, str] | None = None
    attack_type_identity: dict[str, str] | None = None
    device_identity: dict[str, str | bool] | None = None
    device_mac_ip_field: str | None = None
    timestamp_field: str | dict[str, str | bool]
    chronological_ordering_basis: str | None = None
    provenance_fields: list[str]


class EndpointIdentityConfig(StrictFrozenConfigModel):
    resolution: str
    fields: list[str]
    internal_prefix: str
    subnet_component: str
    subnet_role_source: str
    subnet_to_group: dict[int, str]
    excluded_endpoints: dict[str, list[str] | str]
    direction_normalization: str
    use: str
    unresolved_row_policy: str


class RetainedNumericFeaturesConfig(StrictFrozenConfigModel):
    role: Literal["model_feature"]
    order: list[str]
    numeric_parsing: dict[str, list[str] | str]
    on_invalid_value: str


class CategoricalEncodingConfig(StrictFrozenConfigModel):
    strategy: str
    columns: list[str]
    vocabulary_scope: str
    vocabulary_artifact: str
    vocabulary_fingerprint: str
    category_order: str
    encoded_feature_naming: str
    missing_category_policy: str
    unknown_category_policy: str
    unknown_indicator_distinct_from_missing_indicator: bool
    feature_order: list[str]


class ModelFeaturesConfig(StrictFrozenConfigModel):
    role: Literal["model_feature"]
    type: str
    order: list[str]


class MulticlassLabelConfig(StrictFrozenConfigModel):
    column: str
    type: str | None = None
    case: str | None = None


class LabelFieldsConfig(StrictFrozenConfigModel):
    binary_label: dict[str, str | list[int] | list[str]]
    multiclass_label: MulticlassLabelConfig | None = None
    benign_value: dict[str, str | int] | None = None
    attack_class_mapping: dict[str, str] | None = None
    device_family_mapping: dict[str, str] | None = None
    family_taxonomy: str | None = None
    family_map: dict[str, str] | None = None


class DatasetFieldSchemaConfig(StrictFrozenConfigModel):
    source_column_count: int | dict[str, int]
    header_required: bool
    header_must_be_identical_across_all_source_files: bool | None = None
    header_must_be_identical_across_all_files_in_a_tree: bool | None = None
    merged_header_extends_per_class_header_with: str | None = None
    label_column_position: str | None = None
    identity_scheme: IdentitySchemeConfig
    label_fields: LabelFieldsConfig
    model_features: ModelFeaturesConfig | None = None
    source_columns: list[str] | None = None
    endpoint_identity: EndpointIdentityConfig | None = None
    attack_row_group_policy: dict[str, str] | None = None
    retained_numeric_features: RetainedNumericFeaturesConfig | None = None
    post_encoding_feature_order: str | None = None
    categorical_encoding: str | CategoricalEncodingConfig
    leakage_exclusions: list[str] | dict[str, str | list[str]]


class NormalizationSpecConfig(StrictFrozenConfigModel):
    strategy: str
    scope: str


class SplitSpecConfig(StrictFrozenConfigModel):
    method: str
    calibration_benign_only: bool
    split_seed: int | None = None
    ratios: dict[str, float] | None = None
    ordering_basis: str | None = None
    ordering_scope: str | None = None
    gap_handling: str | None = None
    attack_rows: str | None = None
    attack_test_membership: str | None = None
    attack_ordering: str | None = None
    benign_attack_deduplication: str | None = None
    role_order: list[str] | None = None
    excluded_client_folders: list[str] | None = None
    exclusion_reason: str | None = None
    historical_train_fraction: float | None = None
    historical_calibration_fraction: float | None = None
    future_recalibration_fraction: float | None = None
    future_evaluation_fraction: float | None = None
    ordering_field: str | None = None
    ordering_sort: str | None = None
    rollover_policy: str | None = None
    rollover_scope: str | None = None
    boundary_rule: str | None = None
    boundary_index_formula: str | None = None
    future_leakage_check: str | None = None
    minimum_row_counts: dict[str, int] | None = None
    missing_client_policy: str | None = None
    chronology_unverifiable_policy: str | None = None


class MaterializationConfig(StrictFrozenConfigModel):
    materialization_id: str
    role: str | None = None
    normalization: NormalizationSpecConfig
    vocabulary_fit_split: str | None = None
    preprocessing_sequence: list[str]
    row_exclusion: dict[str, str | bool]
    split: SplitSpecConfig
    split_row_semantics: dict[str, str | bool] | None = None
    infeasibility_policy: str | None = None


class SetupClientConstructionConfig(StrictFrozenConfigModel):
    method: str
    client_source: str | list[str] | None = None
    client_semantics: str | None = None
    excluded_client_folders: list[str] | None = None
    client_count: int | None = None
    partition_condition: dict[str, str] | None = None
    source_mixture_components: str | None = None
    label_field: str | None = None
    partition_seed: int | None = None
    partition_axes: dict[str, str] | None = None
    allocation_procedure: dict[str, str] | None = None
    same_proportions_govern: list[str] | None = None
    split_role_preservation: str | None = None
    attack_row_assignment: str | None = None
    attack_labels_used_in_partition_generation: bool | None = None
    minimum_row_counts: dict[str, int] | None = None
    retry_policy: dict[str, str | int] | None = None
    feasibility_failure: str | None = None
    manifest_invariants: list[str] | None = None
    manifest_fields: list[str] | None = None


class SetupConfig(StrictFrozenConfigModel):
    materialization: str
    client_construction: SetupClientConstructionConfig
    provides_capabilities: list[str]
    validation_scope: str | None = None
    eligibility_gate: str | None = None
    client_population_must_equal_setup: str | None = None


class SourceContractConfig(StrictFrozenConfigModel):
    every_model_feature_present_in_merged_header: bool | None = None
    every_model_feature_present_in_every_file: bool | None = None
    model_feature_count_equals_source_column_count: bool | None = None
    per_class_schema_reference_check: dict[str, str | bool] | None = None
    malformed_row: dict[str, str] | None = None
    empty_label_row: dict[str, str] | None = None
    reject_unparseable_numeric_model_feature: bool | None = None
    reject_row_with_field_count_other_than_header: bool | None = None
    column_role_partition: dict[str, list[str] | bool] | None = None
    positional_contract: dict[str, bool] | None = None
    row_integrity_exclusions: dict[str, list[str] | bool | dict[str, dict[str, str]]] | None = None


class FingerprintInputsConfig(StrictFrozenConfigModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, populate_by_name=True)

    source: list[str]
    schema_fields: list[str] = Field(alias="schema")
    materialization: list[str]
    client_assignment: list[str]


class AuthoredDatasetConfig(SchemaVersionOneConfigModel):
    dataset: str
    display_name: str
    schema_id: str
    source_layout: DatasetSourceLayoutConfig
    field_schema: DatasetFieldSchemaConfig
    source_contract: SourceContractConfig
    fingerprint_inputs: FingerprintInputsConfig
    client_identity_contract: dict[str, str | list[str]] | None = None
    eligibility_policy: str
    materializations: dict[str, MaterializationConfig]
    setups: dict[str, SetupConfig]
