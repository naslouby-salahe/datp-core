"""Pydantic 2 models for authored dataset configuration files."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DatasetSourceLayoutConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    root: str
    benign_file: str | None = None
    benign_file_pattern: str | None = None
    attack_file_pattern: str | None = None
    device_dirs: list[str] | None = None
    normal_group_folders: list[str] | None = None
    attack_files: list[str] | None = None
    ignored_source_suffixes: list[str] = Field(default_factory=list)
    ignored_root_entries: list[str] = Field(default_factory=list)
    ignored_subtrees: list[str] = Field(default_factory=list)
    sources: dict[str, Any] | None = None
    executable_source: str | None = None
    cross_source_relationship: dict[str, Any] | None = None
    normal_traffic_root: str | None = None
    attack_traffic_root: str | None = None
    executable_group_folders: list[str] | None = None
    benign_file_required_per_device: bool | None = None
    attack_family_dirs: list[str] | None = None
    attack_family_required_per_device: bool | None = None


class DatasetFieldSchemaConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_column_count: int | dict[str, int]
    header_required: bool = True
    header_must_be_identical_across_all_source_files: bool | None = None
    header_must_be_identical_across_all_files_in_a_tree: bool | None = None
    merged_header_extends_per_class_header_with: str | None = None
    label_column_position: str | None = None
    identity_scheme: dict[str, Any]
    label_fields: dict[str, Any]
    model_features: dict[str, Any] | None = None
    source_columns: list[str] | None = None
    column_types: dict[str, str] | None = None


class AuthoredDatasetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: int = Field(ge=1)
    dataset: str
    display_name: str
    schema_id: str
    source_layout: DatasetSourceLayoutConfig
    field_schema: DatasetFieldSchemaConfig
    setup_profiles: dict[str, Any] | None = None
    source_contract: dict[str, Any] | None = None
    materialization_schemas: dict[str, Any] | None = None

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: int) -> int:
        if value != 1:
            raise ValueError(f"Unsupported dataset schema version: {value}")
        return value
