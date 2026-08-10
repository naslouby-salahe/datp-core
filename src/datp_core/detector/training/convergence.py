"""Convergence early-stop on the relative change of weighted benign validation loss.

Mirrors the historical datp monitor exactly: each completed round records its
weighted aggregate benign validation loss before the stop check, and convergence
is declared on the final completed round. The monitor is authoritative only for
declared convergence protocols; non-convergence training runs the full declared
round budget.
"""

from collections import deque

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject
from datp_core.core.numeric import MetricValue, RoundNumber


class ConvergenceMonitor:
    """Stop federated training when the relative validation-loss change is small.

    ``record`` stores the weighted aggregate benign validation loss of the just
    completed round. ``should_stop`` returns True when convergence has already
    been declared, when the maximum round budget is reached, or when at least
    ``rounds_initial`` rounds and ``window`` recorded losses are available and
    the relative change between the latest and the loss ``window`` rounds ago
    falls strictly below ``relative_threshold``.
    """

    def __init__(
        self,
        *,
        rounds_initial: int,
        rounds_max: int,
        relative_threshold: float,
        window: int,
    ) -> None:
        if rounds_initial < 1:
            raise ValueError("rounds_initial must be >= 1")
        if rounds_max < rounds_initial:
            raise ValueError("rounds_max must be >= rounds_initial")
        if window < 2:
            raise ValueError("window must be >= 2")
        if relative_threshold <= 0.0:
            raise ValueError("relative_threshold must be positive")
        self._rounds_initial = rounds_initial
        self._rounds_max = rounds_max
        self._relative_threshold = relative_threshold
        self._window = window
        self._losses: deque[float] = deque(maxlen=rounds_max)
        self._converged_round: RoundNumber | None = None
        self._latest_relative_change: float | None = None

    @property
    def converged_round(self) -> RoundNumber | None:
        return self._converged_round

    @property
    def num_recorded(self) -> int:
        return len(self._losses)

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
        if server_round >= self._rounds_max:
            return True
        if server_round < self._rounds_initial:
            return False
        if len(self._losses) < self._window:
            return False
        recent = list(self._losses)[-self._window :]
        start_loss = recent[0]
        end_loss = recent[-1]
        if abs(start_loss) < 1e-12:
            relative_change = 0.0
        else:
            relative_change = abs(end_loss - start_loss) / abs(start_loss)
        self._latest_relative_change = relative_change
        if relative_change < self._relative_threshold:
            self._converged_round = round_number
            return True
        return False
