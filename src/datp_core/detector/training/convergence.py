from collections import deque

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject
from datp_core.core.numeric import MetricValue, RoundNumber
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol


class ConvergenceMonitor:
    def __init__(self, protocol: DiagnosticSnapshotProtocol) -> None:
        convergence = protocol.convergence
        if convergence is None:
            raise ValueError("convergence monitor requires a convergence protocol")
        self._rounds_initial = convergence.rounds_initial
        self._rounds_max = protocol.maximum_round
        self._relative_threshold = convergence.relative_threshold
        self._window = convergence.window
        self._losses: deque[float] = deque(maxlen=self._rounds_max.value)
        self._converged_round: RoundNumber | None = None

    @property
    def converged_round(self) -> RoundNumber | None:
        return self._converged_round

    def record(self, weighted_loss: MetricValue) -> None:
        if weighted_loss.value < 0.0:
            raise ScientificContractError(
                ErrorMessage("convergence monitors a non-negative validation loss"),
                subject=ContractSubject.TRAINING,
            )
        self._losses.append(weighted_loss.value)

    def should_stop(self, round_number: RoundNumber) -> bool:
        server_round = round_number.value
        if self._converged_round is not None:
            return True
        if server_round >= self._rounds_max.value:
            return True
        if server_round < self._rounds_initial.value:
            return False
        if len(self._losses) < self._window.value:
            return False
        recent = list(self._losses)[-self._window.value :]
        start_loss = recent[0]
        end_loss = recent[-1]
        if abs(start_loss) < 1e-12:
            relative_change = 0.0
        else:
            relative_change = abs(end_loss - start_loss) / abs(start_loss)
        if relative_change < self._relative_threshold.value:
            self._converged_round = round_number
            return True
        return False
