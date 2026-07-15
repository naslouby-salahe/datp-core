from dataclasses import dataclass
from re import fullmatch

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.claims import ClaimTier, ExecutionStatus, ExperimentRole, validate_role_tier

_EXPERIMENT_ID_PATTERN = r"E-[A-Z]+\d+"
_ARCHITECTURE_CATALOGUE_ID_PATTERN = r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*"
_CELL_ID_PATTERN = rf"{_EXPERIMENT_ID_PATTERN}#[0-9a-f]{{16}}"


def _validated_identity(*, value: str, pattern: str, name: str) -> str:
    if fullmatch(pattern, value) is None:
        raise DomainValidationError(
            detail=f"{name} has an invalid canonical format",
            value=value,
            constraint=pattern,
        )
    return value


def _validated_client_id(value: object) -> None:
    if not isinstance(value, str):
        raise DomainValidationError(detail="client id must be a string", value=repr(value), constraint="string")
    if not value:
        raise DomainValidationError(
            detail="client id must be non-empty", value=repr(value), constraint="non-empty string"
        )
    if any(character.isspace() for character in value):
        raise DomainValidationError(
            detail="client id must be non-empty and contain no whitespace",
            value=repr(value),
            constraint="non-empty string without whitespace",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentId:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(value=self.value, pattern=_EXPERIMENT_ID_PATTERN, name="experiment id")


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientId:
    value: str

    def __post_init__(self) -> None:
        _validated_client_id(self.value)


@dataclass(frozen=True, slots=True, kw_only=True)
class ArchitectureCatalogueId:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(
            value=self.value,
            pattern=_ARCHITECTURE_CATALOGUE_ID_PATTERN,
            name="architecture catalogue id",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class CellId:
    value: str

    def __post_init__(self) -> None:
        _validated_identity(value=self.value, pattern=_CELL_ID_PATTERN, name="cell id")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentIdentity:
    experiment_id: ExperimentId
    evidence_role: ExperimentRole
    tier: ClaimTier
    execution_status: ExecutionStatus

    def __post_init__(self) -> None:
        if not _has_identity_component_types(self):
            raise DomainValidationError(
                detail="experiment identity requires typed identifier, role, tier, and execution status",
                value=repr(self),
                constraint="ExperimentId, ExperimentRole, ClaimTier, ExecutionStatus",
            )
        validate_role_tier(self.evidence_role, self.tier)


def _has_identity_component_types(identity: ExperimentIdentity) -> bool:
    return all(
        (
            type(identity.experiment_id) is ExperimentId,
            type(identity.evidence_role) is ExperimentRole,
            type(identity.tier) is ClaimTier,
            type(identity.execution_status) is ExecutionStatus,
        )
    )
