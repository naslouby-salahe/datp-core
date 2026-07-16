from dataclasses import dataclass

from flwr.server.strategy import FedAvg

from datp_core.domain.errors import DomainValidationError
from datp_core.infrastructure.learning.federation.strategies import (
    FULL_PARTICIPATION_ACCEPT_FAILURES,
    FULL_PARTICIPATION_FRACTION,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowerFedAvgStrategy:
    client_count: int

    def __post_init__(self) -> None:
        if type(self.client_count) is not int or self.client_count <= 0:
            raise DomainValidationError(
                detail="FedAvg requires a positive exact client count",
                value=repr(self.client_count),
                constraint="positive int",
            )

    def build(self) -> FedAvg:
        return FedAvg(
            fraction_fit=FULL_PARTICIPATION_FRACTION,
            fraction_evaluate=FULL_PARTICIPATION_FRACTION,
            min_fit_clients=self.client_count,
            min_evaluate_clients=self.client_count,
            min_available_clients=self.client_count,
            accept_failures=FULL_PARTICIPATION_ACCEPT_FAILURES,
        )
