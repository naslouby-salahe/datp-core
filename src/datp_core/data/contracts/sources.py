"""Source-related contract records."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from attrs import define, field

from datp_core.core.immutability import (
    FrozenJson,
    as_optional_frozen_json_mapping,
    as_optional_str_mapping,
    deep_freeze,
)
from datp_core.core.paths import RelativePath


def _freeze_positional_contract(value: object | None) -> Mapping[str, bool] | None:
    if value is None:
        return None
    return cast("Mapping[str, bool]", deep_freeze(value))


@define(frozen=True, slots=True, kw_only=True)
class ConfiguredSourceTree:
    identifier: str
    root: RelativePath
    file_pattern: str
    expected_column_count: int
    executable: bool
    required_headers: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class DatasetInspectionContract:
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


@define(frozen=True, slots=True, kw_only=True)
class DatasetSourceRecord:
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
class SourceContractRecord:
    every_model_feature_present_in_merged_header: bool | None
    every_model_feature_present_in_every_file: bool | None
    model_feature_count_equals_source_column_count: bool | None
    per_class_schema_reference_check: Mapping[str, FrozenJson] | None = field(
        converter=as_optional_frozen_json_mapping)
    malformed_row: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    empty_label_row: Mapping[str, str] | None = field(converter=as_optional_str_mapping)
    reject_unparseable_numeric_model_feature: bool | None
    reject_row_with_field_count_other_than_header: bool | None
    column_role_partition: Mapping[str, FrozenJson] | None = field(
        converter=as_optional_frozen_json_mapping)
    positional_contract: Mapping[str, bool] | None = field(
        converter=lambda v: _freeze_positional_contract(v))
    row_integrity_exclusions: Mapping[str, FrozenJson] | None = field(
        converter=as_optional_frozen_json_mapping)
