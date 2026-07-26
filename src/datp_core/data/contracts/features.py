"""Feature-related contract records."""

from __future__ import annotations

from collections.abc import Mapping

from attrs import define, field

from datp_core.core.immutability import (
    FrozenJson,
    as_frozen_json_mapping,
    as_int_mapping,
    as_optional_frozen_json_mapping,
    as_optional_str_mapping,
    as_str_mapping,
)


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
    client_identity: Mapping[str, FrozenJson] | None = field(
        converter=as_optional_frozen_json_mapping)
    benign_group_identity: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    attack_row_group_identity: str | None
    label_identity: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    attack_family_identity: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    attack_type_identity: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    device_identity: Mapping[str, FrozenJson] | None = field(
        converter=as_optional_frozen_json_mapping)
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
        converter=lambda v: as_str_mapping({str(k): item for k, item in v.items()})
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
        converter=lambda v: as_frozen_json_mapping(v) if isinstance(v, Mapping) else tuple(v)
    )
