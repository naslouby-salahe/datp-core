"""Source-related contract records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated

from pydantic import BaseModel, ConfigDict
from pydantic.functional_validators import BeforeValidator

from datp_core.core.paths import RelativePath

_OptionalObjectMappingField = Annotated[
    Mapping[str, object] | None,
    BeforeValidator(lambda v: dict(v) if v is not None else None),
]
_OptionalStrMappingField = Annotated[Mapping[str, str] | None, BeforeValidator(lambda v: dict(v) if v is not None else None)]
_PositionalContractField = Annotated[Mapping[str, bool] | None, BeforeValidator(lambda v: dict(v) if v is not None else None)]


class ConfiguredSourceTree(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: str
    root: RelativePath
    file_pattern: str
    expected_column_count: int
    executable: bool
    required_headers: tuple[str, ...]


class DatasetInspectionContract(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class DatasetSourceRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: str
    root: RelativePath
    file_pattern: str
    owns: tuple[str, ...] | None
    permitted_uses: tuple[str, ...] | None
    contributes_rows_to_executable_materializations: bool | None
    defines_pseudo_clients: bool | None


class CrossSourceRelationshipRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    row_count_equality_required: bool
    row_level_one_to_one_equivalence_assumed: bool
    join_by_row_position: str
    join_by_any_key: str


class DatasetSourceLayoutContractRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

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


class SourceContractRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    every_model_feature_present_in_merged_header: bool | None
    every_model_feature_present_in_every_file: bool | None
    model_feature_count_equals_source_column_count: bool | None
    per_class_schema_reference_check: _OptionalObjectMappingField
    malformed_row: _OptionalStrMappingField
    empty_label_row: _OptionalStrMappingField
    reject_unparseable_numeric_model_feature: bool | None
    reject_row_with_field_count_other_than_header: bool | None
    column_role_partition: _OptionalObjectMappingField
    positional_contract: _PositionalContractField
    row_integrity_exclusions: _OptionalObjectMappingField
