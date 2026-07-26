"""FedAvg / FedProx federated training orchestrator."""

from __future__ import annotations

from copy import deepcopy

import torch
from torch import nn

from datp_core.learning.model.determinism import derive_dataloader_shuffle_seed
from datp_core.learning.training.aggregation import (
    validate_federated_training_inputs,
    weighted_average_state,
    weighted_reconstruction_loss,
)
from datp_core.learning.training.local import train_autoencoder
from datp_core.learning.training.models import (
    DataloaderShuffleSeed,
    FederatedCheckpoint,
    FederatedTrainingResult,
)


def federated_train_autoencoder(
    model: nn.Module,
    client_training_data: tuple[tuple[str, torch.Tensor], ...],
    client_calibration_data: tuple[tuple[str, torch.Tensor], ...],
    *,
    rounds: int,
    local_epochs: int,
    learning_rate: float,
    batch_size: int,
    seed: int,
    device: str,
    beta_1: float,
    beta_2: float,
    epsilon: float,
    weight_decay: float,
    amsgrad: bool,
    shuffle_each_epoch: bool,
    checkpoint_rounds: tuple[int, ...],
    shuffle_seed_key: str,
    shuffle_seed_digest_bytes: int,
    proximal_mu: float | None = None,
) -> FederatedTrainingResult:
    """Run full-participation FedAvg or FedProx with client-size weighted aggregation."""
    validate_federated_training_inputs(
        client_training_data,
        client_calibration_data,
        rounds=rounds,
        local_epochs=local_epochs,
        checkpoint_rounds=checkpoint_rounds,
    )
    clients = tuple(sorted(client_training_data, key=lambda item: item[0]))
    calibration_clients = tuple(sorted(client_calibration_data, key=lambda item: item[0]))
    if proximal_mu is not None and proximal_mu <= 0.0:
        raise ValueError("FedProx requires a strictly positive proximal coefficient")

    global_model = deepcopy(model)
    losses: list[tuple[int, float]] = []
    checkpoints: list[FederatedCheckpoint] = []
    derived_seeds: list[DataloaderShuffleSeed] = []
    for round_index in range(rounds):
        round_start = {name: tensor.detach().clone() for name, tensor in global_model.state_dict().items()}
        local_models: list[tuple[int, dict[str, torch.Tensor]]] = []
        for client_id, data in clients:
            local_model = deepcopy(global_model)
            epoch_seeds = tuple(
                derive_dataloader_shuffle_seed(
                    key=shuffle_seed_key,
                    digest_bytes=shuffle_seed_digest_bytes,
                    training_seed=seed,
                    round_number=round_index + 1,
                    client_id=client_id,
                    local_epoch=local_epoch,
                )
                for local_epoch in range(local_epochs)
            )
            derived_seeds.extend(
                DataloaderShuffleSeed(
                    round_number=round_index + 1,
                    client_id=client_id,
                    local_epoch=local_epoch,
                    value=epoch_seed,
                )
                for local_epoch, epoch_seed in enumerate(epoch_seeds)
            )
            trained = train_autoencoder(
                local_model,
                data,
                local_epochs,
                learning_rate,
                batch_size,
                epoch_seeds,
                device,
                beta_1,
                beta_2,
                epsilon,
                weight_decay,
                amsgrad,
                shuffle_each_epoch,
                round_start if proximal_mu is not None else None,
                proximal_mu,
            )
            local_models.append((int(data.shape[0]), trained.state_dict()))
        global_model.load_state_dict(weighted_average_state(local_models))
        round_number = round_index + 1
        losses.append((round_number, weighted_reconstruction_loss(global_model, calibration_clients, device)))
        if round_number in checkpoint_rounds:
            checkpoints.append(
                FederatedCheckpoint(
                    round_number=round_number,
                    state=tuple(
                        (name, value.detach().cpu().clone()) for name, value in global_model.state_dict().items()
                    ),
                )
            )
    return FederatedTrainingResult(
        model=global_model,
        round_losses=tuple(losses),
        scheduled_checkpoints=tuple(checkpoints),
        derived_shuffle_seeds=tuple(derived_seeds),
    )
