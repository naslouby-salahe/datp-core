"""DATP-Core typed errors."""

from enum import Enum


def _subject_token(subject: Enum | None) -> str | None:
    if subject is None:
        return None
    value = subject.value
    return value if isinstance(value, str) else str(value)


class DatpCoreError(Exception):
    def __init__(
        self,
        message: str,
        *,
        subject: Enum | None = None,
        reason: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.subject = _subject_token(subject)
        self.reason = reason


class ScientificContractError(DatpCoreError):
    pass


def require_contract(condition: bool, message: str, subject: Enum | None = None) -> None:
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
