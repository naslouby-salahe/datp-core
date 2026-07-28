"""Dataset-specific source contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, PositiveInt, model_validator

from datp_core.core.identifiers import ClientId
from datp_core.core.paths import RelativePath
from datp_core.data.contracts.base import StrictFrozenModel
from datp_core.data.contracts.enums import (
    AdapterKind,
    ClientIdentityMethod,
    InvalidRowPolicy,
    LabelCasePolicy,
    SourceDiscoveryMode,
    SourceRole,
    SourceTreeKind,
)
from datp_core.data.contracts.values import (
    AttackFamilyName,
    CategoryToken,
    ColumnName,
    FeatureName,
    LabelValue,
    SourceTreeId,
)


class SourceTreeConfig(StrictFrozenModel):
    identifier: SourceTreeId
    kind: SourceTreeKind
    role: SourceRole
    root: RelativePath
    file_pattern: str
    discovery: SourceDiscoveryMode
    expected_column_count: PositiveInt
    required_headers: tuple[ColumnName, ...]
    headers_must_be_identical: bool


class SourceInventoryPolicy(StrictFrozenModel):
    ignored_suffixes: tuple[str, ...]
    ignored_subtrees: tuple[RelativePath, ...]
    ignored_root_entries: tuple[str, ...]


class FileNameClientIdentity(StrictFrozenModel):
    method: Literal[ClientIdentityMethod.FILE_NAME]


class RelativePathClientIdentity(StrictFrozenModel):
    method: Literal[ClientIdentityMethod.RELATIVE_PATH_COMPONENT]
    component_index: int

    @model_validator(mode="after")
    def validate_component_index(self) -> RelativePathClientIdentity:
        if self.component_index < 0:
            raise ValueError("component_index must be non-negative")
        return self


type ClientIdentityConfig = Annotated[
    FileNameClientIdentity | RelativePathClientIdentity,
    Field(discriminator="method"),
]


class CICIoT2023SourceConfig(StrictFrozenModel):
    adapter: Literal[AdapterKind.CICIOT2023]
    tree: SourceTreeConfig
    inventory: SourceInventoryPolicy
    feature_columns: tuple[FeatureName, ...]
    multiclass_label_column: ColumnName
    benign_label: LabelValue
    label_case_policy: LabelCasePolicy
    client_identity: FileNameClientIdentity
    invalid_row_policy: InvalidRowPolicy

    @model_validator(mode="after")
    def validate_tree(self) -> CICIoT2023SourceConfig:
        if self.tree.kind is not SourceTreeKind.MERGED or self.tree.role is not SourceRole.EXECUTABLE:
            raise ValueError("CICIoT2023 requires one executable merged source tree")
        expected = tuple(column.value for column in self.feature_columns) + (self.multiclass_label_column.value,)
        observed = tuple(column.value for column in self.tree.required_headers)
        if expected != observed:
            raise ValueError("CICIoT2023 required headers must exactly match features followed by the label column")
        return self


class NBaIoTSourceConfig(StrictFrozenModel):
    adapter: Literal[AdapterKind.NBAIOT]
    tree: SourceTreeConfig
    inventory: SourceInventoryPolicy
    feature_columns: tuple[FeatureName, ...]
    client_identity: RelativePathClientIdentity
    device_directories: tuple[ClientId, ...]
    excluded_device_directories: tuple[ClientId, ...]
    benign_filename: str
    benign_file_required_per_device: bool
    attack_family_directories: tuple[AttackFamilyName, ...]
    attack_family_required_per_device: bool
    invalid_row_policy: InvalidRowPolicy

    @model_validator(mode="after")
    def validate_tree(self) -> NBaIoTSourceConfig:
        if self.tree.kind is not SourceTreeKind.DEVICE_HIERARCHY or self.tree.role is not SourceRole.EXECUTABLE:
            raise ValueError("N-BaIoT requires one executable device-hierarchy tree")
        if self.invalid_row_policy is not InvalidRowPolicy.FAIL_SOURCE:
            raise ValueError("N-BaIoT source integrity requires fail_source invalid-row handling")
        if not self.benign_filename.strip():
            raise ValueError("benign_filename must not be blank")
        return self


class EdgeIIoTsetSourceConfig(StrictFrozenModel):
    adapter: Literal[AdapterKind.EDGE_IIOTSET]
    benign_trees: tuple[SourceTreeConfig, ...]
    attack_reference_trees: tuple[SourceTreeConfig, ...]
    inventory: SourceInventoryPolicy
    numeric_columns: tuple[FeatureName, ...]
    categorical_columns: tuple[ColumnName, ...]
    binary_label_column: ColumnName
    multiclass_label_column: ColumnName
    timestamp_column: ColumnName
    benign_label: LabelValue
    label_case_policy: LabelCasePolicy
    client_identity: RelativePathClientIdentity
    expected_clients: tuple[ClientId, ...]
    excluded_clients: tuple[ClientId, ...]
    missing_category_token: CategoryToken
    unknown_category_token: CategoryToken
    invalid_row_policy: InvalidRowPolicy

    @model_validator(mode="after")
    def validate_trees(self) -> EdgeIIoTsetSourceConfig:
        if not self.benign_trees:
            raise ValueError("Edge-IIoTset requires executable benign source trees")
        if any(
            tree.kind is not SourceTreeKind.BENIGN_GROUPS or tree.role is not SourceRole.EXECUTABLE
            for tree in self.benign_trees
        ):
            raise ValueError("Edge-IIoTset benign trees must be executable benign-group trees")
        if any(
            tree.kind is not SourceTreeKind.ATTACK_REFERENCE or tree.role is not SourceRole.AUDIT_ONLY
            for tree in self.attack_reference_trees
        ):
            raise ValueError("Edge-IIoTset attack trees must be audit-only references")
        if self.missing_category_token == self.unknown_category_token:
            raise ValueError("missing and unknown category tokens must be distinct")
        return self


type DatasetSourceConfig = Annotated[
    CICIoT2023SourceConfig | NBaIoTSourceConfig | EdgeIIoTsetSourceConfig,
    Field(discriminator="adapter"),
]
