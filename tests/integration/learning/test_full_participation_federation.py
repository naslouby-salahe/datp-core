from typing import cast

import pytest
import torch

from datp_core.domain.errors import (
    ClientShapeMismatchError,
    MalformedClientUpdateError,
    NonFiniteClientUpdateError,
    RoundAbortedError,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.runtime.seeds import RoundNumber
from datp_core.infrastructure.learning.federation.strategies.fedavg import FlowerFedAvgStrategy
from datp_core.infrastructure.learning.federation.strategies.fedprox import FlowerFedProxStrategy
from datp_core.infrastructure.learning.federation.trainer import (
    ClientModelUpdate,
    validate_full_participation_updates,
    weighted_fedavg,
)


def _update(client: str, values: tuple[float, ...], *, samples: int = 1) -> ClientModelUpdate:
    return ClientModelUpdate(
        client_id=ClientId(value=client),
        tensors=(torch.tensor(values),),
        sample_count=samples,
    )


def test_full_participation_rejects_missing_and_malformed_updates() -> None:
    expected = (ClientId(value="client-a"), ClientId(value="client-b"))

    with pytest.raises(RoundAbortedError):
        validate_full_participation_updates(
            expected_clients=expected,
            updates=(_update("client-a", (1.0,)),),
            round_number=RoundNumber(value=1),
        )
    with pytest.raises(MalformedClientUpdateError):
        validate_full_participation_updates(
            expected_clients=expected,
            updates=(_update("client-a", (1.0,), samples=0), _update("client-b", (1.0,))),
            round_number=RoundNumber(value=1),
        )
    with pytest.raises(MalformedClientUpdateError):
        validate_full_participation_updates(
            expected_clients=expected,
            updates=(
                ClientModelUpdate(
                    client_id=ClientId(value="client-a"),
                    tensors=cast(tuple[torch.Tensor, ...], ("not-a-tensor",)),
                    sample_count=1,
                ),
                _update("client-b", (1.0,)),
            ),
            round_number=RoundNumber(value=1),
        )


def test_full_participation_rejects_nonfinite_and_shape_incompatible_updates() -> None:
    expected = (ClientId(value="client-a"), ClientId(value="client-b"))

    with pytest.raises(NonFiniteClientUpdateError):
        validate_full_participation_updates(
            expected_clients=expected,
            updates=(_update("client-a", (1.0,)), _update("client-b", (float("nan"),))),
            round_number=RoundNumber(value=1),
        )
    with pytest.raises(ClientShapeMismatchError):
        validate_full_participation_updates(
            expected_clients=expected,
            updates=(_update("client-a", (1.0,)), _update("client-b", (1.0, 2.0))),
            round_number=RoundNumber(value=1),
        )


def test_weighted_fedavg_is_deterministic_after_full_participation_validation() -> None:
    updates = (_update("client-a", (1.0, 3.0), samples=1), _update("client-b", (5.0, 7.0), samples=3))

    validate_full_participation_updates(
        expected_clients=(ClientId(value="client-a"), ClientId(value="client-b")),
        updates=updates,
        round_number=RoundNumber(value=1),
    )

    assert torch.equal(weighted_fedavg(updates)[0], torch.tensor((4.0, 6.0)))


def test_flower_strategies_require_every_client_and_keep_fedprox_mu_explicit() -> None:
    fedavg = FlowerFedAvgStrategy(client_count=2).build()
    fedprox = FlowerFedProxStrategy(client_count=2, proximal_mu=0.01).build()

    assert fedavg.accept_failures is False
    assert fedavg.min_fit_clients == fedavg.min_available_clients == 2
    assert fedprox.accept_failures is False
    assert fedprox.proximal_mu == 0.01
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
