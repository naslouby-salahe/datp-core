"""DATP-Core typed errors."""

from enum import Enum


def _subject_token(subject: str | Enum | None) -> str | None:
    if subject is None:
        return None
    if isinstance(subject, Enum):
        value = subject.value
        return value if isinstance(value, str) else str(value)
    return subject


class DatpCoreError(Exception):
    def __init__(
        self,
        message: str,
        *,
        subject: str | Enum | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.subject = _subject_token(subject)
        self.reason = reason


class ScientificContractError(DatpCoreError):
    pass


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
