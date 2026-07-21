"""FedProx uses the locked proximal objective, not a renamed FedAvg loop."""

import pytest
import torch

from datp_core.infrastructure.learning.pytorch_adapter import (
    DynamicDenseAutoencoder,
    federated_train_autoencoder,
    fedprox_objective,
)


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


def test_federated_training_runs_full_participation_for_fedavg_and_fedprox() -> None:
    clients = (
        ("a", torch.tensor([[1.0], [2.0]])),
        ("b", torch.tensor([[3.0], [4.0], [5.0]])),
    )
    kwargs = {
        "rounds": 1,
        "local_epochs": 1,
        "learning_rate": 0.01,
        "batch_size": 2,
        "seed": 7,
        "device": "cpu",
        "beta_1": 0.9,
        "beta_2": 0.999,
        "epsilon": 1.0e-8,
        "weight_decay": 0.0,
        "amsgrad": False,
        "shuffle_each_epoch": False,
        "checkpoint_rounds": (1,),
    }
    fedavg = federated_train_autoencoder(DynamicDenseAutoencoder(1, (1,)), clients, **kwargs)
    fedprox = federated_train_autoencoder(DynamicDenseAutoencoder(1, (1,)), clients, proximal_mu=0.1, **kwargs)

    assert set(fedavg.model.state_dict()) == set(fedprox.model.state_dict())
    assert len(fedavg.round_losses) == len(fedprox.round_losses) == 1
    assert fedavg.scheduled_checkpoints[0].round_number == 1
