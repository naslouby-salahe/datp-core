from dataclasses import dataclass

from flwr.server.strategy import FedAvg

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.training import ParticipationStrategy


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
        participation_fraction = ParticipationStrategy.FULL.required_participation_fraction()
        return FedAvg(
            fraction_fit=participation_fraction,
            fraction_evaluate=participation_fraction,
            min_fit_clients=self.client_count,
            min_evaluate_clients=self.client_count,
            min_available_clients=self.client_count,
            accept_failures=ParticipationStrategy.FULL.permits_round_failures(),
        )
