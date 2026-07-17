from dataclasses import dataclass

from flwr.server.strategy import FedProx

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.training import FEDPROX_MU_GRID, ParticipationStrategy


@dataclass(frozen=True, slots=True, kw_only=True)
class FlowerFedProxStrategy:
    client_count: int
    proximal_mu: float

    def __post_init__(self) -> None:
        if type(self.client_count) is not int or self.client_count <= 0:
            raise DomainValidationError(
                detail="FedProx requires a positive exact client count",
                value=repr(self.client_count),
                constraint="positive int",
            )
        if type(self.proximal_mu) is not float or self.proximal_mu not in FEDPROX_MU_GRID:
            raise DomainValidationError(
                detail="FedProx requires a pre-registered proximal coefficient",
                value=repr(self.proximal_mu),
                constraint=repr(FEDPROX_MU_GRID),
            )

    def build(self) -> FedProx:
        participation_fraction = ParticipationStrategy.FULL.required_participation_fraction()
        return FedProx(
            fraction_fit=participation_fraction,
            fraction_evaluate=participation_fraction,
            min_fit_clients=self.client_count,
            min_evaluate_clients=self.client_count,
            min_available_clients=self.client_count,
            accept_failures=ParticipationStrategy.FULL.permits_round_failures(),
            proximal_mu=self.proximal_mu,
        )
