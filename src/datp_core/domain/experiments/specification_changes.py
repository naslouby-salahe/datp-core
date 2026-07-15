from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn

from datp_core.domain.artifacts.keys import StorageRootKind
from datp_core.domain.artifacts.lineage import ReuseImpact
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.protocols import ScientificProtocolField
from datp_core.domain.runtime.policies import PipelineStage


class ExecutionPolicyField(StrEnum):
    MODE = "mode"
    DEVICE = "device"
    BUDGET = "budget"
    PARALLELISM = "parallelism"
    SEED_ROLES = "seed_roles"
    RESOURCE_PRESSURE = "resource_pressure"
    RECOVERY = "recovery"


class EnvironmentField(StrEnum):
    STORAGE_ROOTS = "storage_roots"


@dataclass(frozen=True, slots=True, kw_only=True)
class StorageRootDescriptor:
    kind: StorageRootKind
    descriptor: str

    def __post_init__(self) -> None:
        _validate_storage_root_kind(self.kind)
        _validate_storage_root_descriptor(self.descriptor)


def _validate_storage_root_kind(kind: object) -> None:
    if type(kind) is not StorageRootKind:
        _raise_invalid_storage_root_descriptor(kind)


def _validate_storage_root_descriptor(descriptor: object) -> None:
    if not isinstance(descriptor, str):
        _raise_invalid_storage_root_descriptor(descriptor)
    _validate_nonempty_storage_root_descriptor(descriptor)
    _validate_storage_root_descriptor_characters(descriptor)


def _validate_nonempty_storage_root_descriptor(descriptor: str) -> None:
    if not descriptor:
        _raise_invalid_storage_root_descriptor(descriptor)


def _validate_storage_root_descriptor_characters(descriptor: str) -> None:
    if any(character.isspace() for character in descriptor):
        _raise_invalid_storage_root_descriptor(descriptor)
    if "/" in descriptor or "\\" in descriptor:
        _raise_invalid_storage_root_descriptor(descriptor)


def _raise_invalid_storage_root_descriptor(value: object) -> NoReturn:
    raise DomainValidationError(
        detail="storage-root descriptor must be a non-empty non-path token",
        value=repr(value),
        constraint="non-empty token without whitespace or path separators",
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class EnvironmentSpecification:
    storage_roots: tuple[StorageRootDescriptor, ...]

    def __post_init__(self) -> None:
        if type(self.storage_roots) is not tuple or any(
            type(descriptor) is not StorageRootDescriptor for descriptor in self.storage_roots
        ):
            raise DomainValidationError(
                detail="environment requires typed storage-root descriptors",
                value=repr(self.storage_roots),
                constraint="tuple[StorageRootDescriptor, ...]",
            )
        kinds = tuple(descriptor.kind for descriptor in self.storage_roots)
        if len(set(kinds)) != len(kinds):
            raise DomainValidationError(
                detail="environment storage-root descriptors must have unique kinds",
                value=repr(kinds),
                constraint="one descriptor per StorageRootKind",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ScientificSpecificationChange:
    field: ScientificProtocolField
    affected_stages: tuple[PipelineStage, ...]
    reuse_impact: ReuseImpact

    def __post_init__(self) -> None:
        _validate_change(
            field=self.field,
            expected_field_type=ScientificProtocolField,
            reuse_impact=self.reuse_impact,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExecutionPolicyChange:
    field: ExecutionPolicyField
    affected_stages: tuple[PipelineStage, ...]
    reuse_impact: ReuseImpact

    def __post_init__(self) -> None:
        _validate_change(
            field=self.field,
            expected_field_type=ExecutionPolicyField,
            reuse_impact=self.reuse_impact,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class EnvironmentChange:
    field: EnvironmentField
    affected_stages: tuple[PipelineStage, ...]
    reuse_impact: ReuseImpact

    def __post_init__(self) -> None:
        _validate_change(
            field=self.field,
            expected_field_type=EnvironmentField,
            reuse_impact=self.reuse_impact,
        )


type SpecificationChange = ScientificSpecificationChange | ExecutionPolicyChange | EnvironmentChange


def _validate_change(
    *,
    field: object,
    expected_field_type: type[StrEnum],
    reuse_impact: object,
) -> None:
    if type(field) is not expected_field_type:
        raise DomainValidationError(
            detail="specification change requires its declared field enum",
            value=repr(field),
            constraint=expected_field_type.__name__,
        )
    if type(reuse_impact) is not ReuseImpact:
        raise DomainValidationError(
            detail="specification change requires one reuse impact",
            value=repr(reuse_impact),
            constraint="ReuseImpact",
        )
