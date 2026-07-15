import pytest
import torch

from datp_core.domain.errors import NonFiniteClientUpdateError, RoundAbortedError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.runtime.seeds import RoundNumber
from datp_core.infrastructure.learning.federation.strategies.fedavg import FlowerFedAvgStrategy
from datp_core.infrastructure.learning.federation.strategies.fedprox import FlowerFedProxStrategy
from datp_core.infrastructure.learning.federation.trainer import ClientModelUpdate, validate_full_participation_updates
from tests.support.cuda_lane import skip_if_cuda_unavailable


@pytest.mark.cuda
def test_cuda_full_participation_and_fedprox_equivalence_on_synthetic_parameters() -> None:
    skip_if_cuda_unavailable()
    expected = (ClientId(value="client-a"), ClientId(value="client-b"))
    valid_parameter = torch.ones(1, device="cuda")

    with pytest.raises(RoundAbortedError):
        validate_full_participation_updates(
            expected_clients=expected,
            updates=(ClientModelUpdate(client_id=expected[0], tensors=(valid_parameter,), sample_count=1),),
            round_number=RoundNumber(value=1),
        )
    with pytest.raises(NonFiniteClientUpdateError):
        validate_full_participation_updates(
            expected_clients=expected,
            updates=(
                ClientModelUpdate(client_id=expected[0], tensors=(valid_parameter,), sample_count=1),
                ClientModelUpdate(
                    client_id=expected[1],
                    tensors=(torch.tensor((float("nan"),), device="cuda"),),
                    sample_count=1,
                ),
            ),
            round_number=RoundNumber(value=1),
        )

    fedavg = FlowerFedAvgStrategy(client_count=2).build()
    fedprox = FlowerFedProxStrategy(client_count=2, proximal_mu=0.01).build()
    assert (
        fedprox.fraction_fit,
        fedprox.fraction_evaluate,
        fedprox.min_fit_clients,
        fedprox.min_evaluate_clients,
        fedprox.min_available_clients,
        fedprox.accept_failures,
    ) == (
        fedavg.fraction_fit,
        fedavg.fraction_evaluate,
        fedavg.min_fit_clients,
        fedavg.min_evaluate_clients,
        fedavg.min_available_clients,
        fedavg.accept_failures,
    )
