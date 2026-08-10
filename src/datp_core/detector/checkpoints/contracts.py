from dataclasses import dataclass

from pydantic import model_validator

from datp_core.core.contracts import StrictModel
from datp_core.core.numeric import RoundNumber


@dataclass(frozen=True, slots=True)
class ConvergenceProtocol:
    rounds_initial: RoundNumber
    relative_threshold: float
    window: int

    def __post_init__(self) -> None:
        if self.rounds_initial.value < 1:
            raise ValueError("rounds_initial must be >= 1")
        if self.window < 2:
            raise ValueError("window must be >= 2")
        if self.relative_threshold <= 0.0:
            raise ValueError("relative_threshold must be positive")


class DiagnosticSnapshotProtocol(StrictModel):
    diagnostic_rounds: tuple[RoundNumber, ...]
    maximum_round: RoundNumber
    convergence: ConvergenceProtocol | None = None

    @model_validator(mode="after")
    def validate_diagnostic_rounds(self) -> "DiagnosticSnapshotProtocol":
        values = tuple(round_number.value for round_number in self.diagnostic_rounds)
        if values != tuple(sorted(values)) or len(frozenset(values)) != len(values):
            raise ValueError("diagnostic rounds must be unique and ordered")
        if any(value > self.maximum_round.value for value in values):
            raise ValueError("diagnostic rounds cannot exceed the maximum round")
        if self.convergence is not None and self.convergence.rounds_initial.value > self.maximum_round.value:
            raise ValueError("rounds_initial cannot exceed the maximum round")
        return self
