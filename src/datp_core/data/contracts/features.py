"""Feature-related contract records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated

from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import BeforeValidator

from datp_core.core.immutability import (
    FrozenJson,
    as_frozen_json_mapping,
    as_int_mapping,
    as_optional_frozen_json_mapping,
    as_optional_str_mapping,
    as_str_mapping,
)

# ---- Custom conversion helpers ----


def _convert_source_column_count(v: object) -> int | Mapping[str, int]:
    return v if isinstance(v, int) else as_int_mapping(v)


def _convert_timestamp_field(v: object) -> str | Mapping[str, FrozenJson]:
    return v if isinstance(v, str) else as_frozen_json_mapping(v)


def _convert_leakage_exclusions(
    v: object,
) -> tuple[str, ...] | Mapping[str, FrozenJson]:
    return as_frozen_json_mapping(v) if isinstance(v, Mapping) else tuple(v)


def _convert_subnet_to_group(v: object) -> Mapping[str, str]:
    return as_str_mapping({str(k): item for k, item in v.items()})


# ---- Annotated field types with conversion validators ----

_FrozenJsonMappingField = Annotated[Mapping[str, FrozenJson], BeforeValidator(as_frozen_json_mapping)]
_OptionalFrozenJsonMappingField = Annotated[
    Mapping[str, FrozenJson] | None,
    BeforeValidator(as_optional_frozen_json_mapping),
]
_OptionalStrMappingField = Annotated[Mapping[str, str] | None, BeforeValidator(as_optional_str_mapping)]
_StrMappingField = Annotated[Mapping[str, str], BeforeValidator(as_str_mapping)]
_SourceColumnCountField = Annotated[int | Mapping[str, int], BeforeValidator(_convert_source_column_count)]
_TimestampField = Annotated[str | Mapping[str, FrozenJson], BeforeValidator(_convert_timestamp_field)]
_SubnetToGroupField = Annotated[Mapping[str, str], BeforeValidator(_convert_subnet_to_group)]
_LeakageExclusionsField = Annotated[
    tuple[str, ...] | Mapping[str, FrozenJson],
    BeforeValidator(_convert_leakage_exclusions),
]


class MulticlassLabelRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    column: str
    type: str | None
    case: str | None


class LabelFieldsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    binary_label: _FrozenJsonMappingField
    multiclass_label: MulticlassLabelRecord | None
    benign_value: _OptionalFrozenJsonMappingField
    attack_class_mapping: _OptionalStrMappingField
    device_family_mapping: _OptionalStrMappingField
    family_taxonomy: str | None
    family_map: _OptionalStrMappingField


class IdentitySchemeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_identity: _FrozenJsonMappingField
    client_identity: _OptionalFrozenJsonMappingField
    benign_group_identity: _OptionalStrMappingField
    attack_row_group_identity: str | None
    label_identity: _OptionalStrMappingField
    attack_family_identity: _OptionalStrMappingField
    attack_type_identity: _OptionalStrMappingField
    device_identity: _OptionalFrozenJsonMappingField
    device_mac_ip_field: str | None
    timestamp_field: _TimestampField
    chronological_ordering_basis: str | None
    provenance_fields: tuple[str, ...]


class EndpointIdentityRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    resolution: str
    fields: tuple[str, ...]
    internal_prefix: str
    subnet_component: str
    subnet_role_source: str
    subnet_to_group: _SubnetToGroupField
    excluded_endpoints: _FrozenJsonMappingField
    direction_normalization: str
    use: str
    unresolved_row_policy: str


class RetainedNumericFeaturesRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    order: tuple[str, ...]
    numeric_parsing: _FrozenJsonMappingField
    on_invalid_value: str


class CategoricalEncodingRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class ModelFeaturesRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    type: str
    order: tuple[str, ...]


class DatasetFieldSchemaRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_column_count: _SourceColumnCountField
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
    attack_row_group_policy: _OptionalStrMappingField
    retained_numeric_features: RetainedNumericFeaturesRecord | None
    post_encoding_feature_order: str | None
    categorical_encoding: str | CategoricalEncodingRecord
    leakage_exclusions: _LeakageExclusionsField
