"""DATP-Core typed errors."""

from enum import Enum, StrEnum
from typing import ClassVar

from datp_core.core.identifiers import NonEmptyString


class ErrorMessage(NonEmptyString):
    validation_name: ClassVar[str] = "error message"


class MissingPrerequisiteReason(StrEnum):
    """Controlled discriminants for :class:`MissingPrerequisiteError` callers that branch on cause."""

    ANCHOR_GATE = "anchor_gate"


def _subject_token(subject: Enum | None) -> str | None:
    if subject is None:
        return None
    value = subject.value
    return value if isinstance(value, str) else str(value)


class DatpCoreError(Exception):
    def __init__(
        self,
        message: ErrorMessage,
        *,
        subject: Enum | None = None,
        reason: Enum | None = None,
    ) -> None:
        super().__init__(str(message))
        self.message = message
        self.subject = _subject_token(subject)
        self.reason = reason


class ScientificContractError(DatpCoreError):
    pass


def require_contract(condition: bool, message: ErrorMessage, subject: Enum | None = None) -> None:
    if not condition:
        raise ScientificContractError(message, subject=subject)


class UnresolvedScientificValueError(ScientificContractError):
    pass


class CapabilityError(DatpCoreError):
    pass


class InfeasibleExperimentError(DatpCoreError):
    pass


class DataIntegrityError(DatpCoreError):
    pass


class LeakageError(DatpCoreError):
    pass


class AnchorReproductionError(DatpCoreError):
    pass


class ProtocolValidationError(DatpCoreError):
    pass


class SerializationSafetyError(DatpCoreError):
    pass


class ArtifactIntegrityError(DatpCoreError):
    pass


class ExecutionStateError(DatpCoreError):
    pass


class UnknownIdentifierError(DatpCoreError):
    pass


class MissingPrerequisiteError(DatpCoreError):
    pass


class ReportEvidenceError(DatpCoreError):
    pass


class CliExitCode(Enum):
    """Stable CLI exit codes for typed domain failures."""

    SUCCESS = 0
    USAGE = 2
    INVALID_DECLARATION = 10
    UNKNOWN_IDENTIFIER = 11
    MISSING_RAW_DATASET = 12
    INVALID_CANONICAL_DATASET = 13
    PROVENANCE_FAILURE = 14
    INCOMPLETE_PREREQUISITE = 15
    ANCHOR_GATE_FAILURE = 16
    EXPERIMENT_FAILURE = 17
    INVALID_ARTIFACT = 18
    MISSING_REPORT_EVIDENCE = 19
    REPORT_FAILURE = 20
    SCIENTIFIC_CONTRACT = 30
    INTERNAL = 1
