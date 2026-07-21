"""FedProx uses the locked proximal objective, not a renamed FedAvg loop."""

import pytest
import torch

from datp_core.infrastructure.learning.pytorch_adapter import fedprox_objective


def test_fedprox_objective_adds_half_mu_squared_distance_to_round_start_state() -> None:
    model = torch.nn.Linear(1, 1, bias=False)
    with torch.no_grad():
        model.weight.fill_(3.0)
    base_loss = torch.tensor(2.0)
    reference = {"weight": torch.tensor([[1.0]])}

    objective = fedprox_objective(base_loss, model, reference, proximal_mu=0.5)

    assert objective.item() == pytest.approx(3.0)


def test_fedprox_rejects_nonpositive_coefficient_and_mismatched_state() -> None:
    model = torch.nn.Linear(1, 1, bias=False)
    with pytest.raises(ValueError, match="strictly positive"):
        fedprox_objective(torch.tensor(0.0), model, {"weight": torch.zeros((1, 1))}, proximal_mu=0.0)
    with pytest.raises(ValueError, match="exactly match"):
        fedprox_objective(torch.tensor(0.0), model, {}, proximal_mu=0.1)
