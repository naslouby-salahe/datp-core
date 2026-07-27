"""Feature-related contract records."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Annotated, cast

from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import BeforeValidator


def _convert_source_column_count(v: object) -> int | Mapping[str, int]:
    return v if isinstance(v, int) else dict(cast("Iterable[tuple[str, int]]", v))


def _convert_timestamp_field(v: object) -> str | Mapping[str, object]:
    return v if isinstance(v, str) else dict(cast("Iterable[tuple[str, object]]", v))


def _convert_leakage_exclusions(
    v: object,
) -> tuple[str, ...] | Mapping[str, object]:
    if isinstance(v, Mapping):
        return dict(cast("Iterable[tuple[str, object]]", v))
    if isinstance(v, Iterable):
        return tuple(v)
    raise TypeError(f"Leakage exclusions must be a mapping or iterable, got {type(v).__name__}")


def _convert_subnet_to_group(v: object) -> Mapping[str, str]:
    if not isinstance(v, Mapping):
        raise TypeError(f"Subnet-to-group mapping requires a mapping, got {type(v).__name__}")
    return {str(k): item for k, item in v.items()}


_JsonMappingField = Annotated[Mapping[str, object], BeforeValidator(dict)]
_OptionalJsonMappingField = Annotated[
    Mapping[str, object] | None,
    BeforeValidator(lambda v: dict(v) if v is not None else None),
]
_OptionalStrMappingField = Annotated[
    Mapping[str, str] | None,
    BeforeValidator(lambda v: dict(v) if v is not None else None),
]
_StrMappingField = Annotated[Mapping[str, str], BeforeValidator(dict)]
_SourceColumnCountField = Annotated[
    int | Mapping[str, int],
    BeforeValidator(_convert_source_column_count),
]
_TimestampField = Annotated[str | Mapping[str, object], BeforeValidator(_convert_timestamp_field)]
_SubnetToGroupField = Annotated[Mapping[str, str], BeforeValidator(_convert_subnet_to_group)]
_LeakageExclusionsField = Annotated[
    tuple[str, ...] | Mapping[str, object],
    BeforeValidator(_convert_leakage_exclusions),
]


class MulticlassLabelRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    column: str
    type: str | None
    case: str | None


class LabelFieldsRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    binary_label: _JsonMappingField
    multiclass_label: MulticlassLabelRecord | None
    benign_value: _OptionalJsonMappingField
    attack_class_mapping: _OptionalStrMappingField
    device_family_mapping: _OptionalStrMappingField
    family_taxonomy: str | None
    family_map: _OptionalStrMappingField


class IdentitySchemeRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_identity: _JsonMappingField
    client_identity: _OptionalJsonMappingField
    benign_group_identity: _OptionalStrMappingField
    attack_row_group_identity: str | None
    label_identity: _OptionalStrMappingField
    attack_family_identity: _OptionalStrMappingField
    attack_type_identity: _OptionalStrMappingField
    device_identity: _OptionalJsonMappingField
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
    excluded_endpoints: _JsonMappingField
    direction_normalization: str
    use: str
    unresolved_row_policy: str


class RetainedNumericFeaturesRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    order: tuple[str, ...]
    numeric_parsing: _JsonMappingField
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
