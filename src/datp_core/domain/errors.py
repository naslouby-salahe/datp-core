"""DATP-Core typed errors."""


class DatpCoreError(Exception):
    def __init__(self, message: str, *, subject: str | None = None, reason: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.subject = subject
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
