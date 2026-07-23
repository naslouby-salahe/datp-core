"""Ditto model-personalization training: aggregated global state plus persistent, never-aggregated
per-client personalized states, trained against a proximal objective toward the round-start global.
"""

from __future__ import annotations

from copy import deepcopy

import torch
import torch.nn as nn
from attrs import define

from datp_core.learning.autoencoder import derive_dataloader_shuffle_seed
from datp_core.learning.federated import (
    DataloaderShuffleSeed,
    train_autoencoder,
    validate_federated_training_inputs,
    weighted_average_state,
    weighted_reconstruction_loss,
)


@define(frozen=True, slots=True, kw_only=True)
class DittoCheckpoint:
    round_number: int
    global_state: tuple[tuple[str, torch.Tensor], ...]
    personalized_states: tuple[tuple[str, tuple[tuple[str, torch.Tensor], ...]], ...]


@define(frozen=True, slots=True, kw_only=True)
class DittoTrainingResult:
    global_model: nn.Module
    personalized_models: tuple[tuple[str, nn.Module], ...]
    global_round_losses: tuple[tuple[int, float], ...]
    personalized_round_losses: tuple[tuple[int, float], ...]
    scheduled_checkpoints: tuple[DittoCheckpoint, ...]
    derived_shuffle_seeds: tuple[DataloaderShuffleSeed, ...]


def ditto_train_autoencoder(
    model: nn.Module,
    client_training_data: tuple[tuple[str, torch.Tensor], ...],
    client_calibration_data: tuple[tuple[str, torch.Tensor], ...],
    *,
    rounds: int,
    local_epochs: int,
    personalized_local_epochs: int,
    proximal_weight: float,
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
) -> DittoTrainingResult:
    """Train Ditto's aggregated global state and persistent, never-aggregated client states."""
    validate_federated_training_inputs(
        client_training_data,
        client_calibration_data,
        rounds=rounds,
        local_epochs=local_epochs,
        checkpoint_rounds=checkpoint_rounds,
    )
    if personalized_local_epochs < 1 or proximal_weight <= 0.0:
        raise ValueError("Ditto requires positive personalized local epochs and proximal weight")
    clients = tuple(sorted(client_training_data, key=lambda item: item[0]))
    calibration_clients = tuple(sorted(client_calibration_data, key=lambda item: item[0]))
    global_model = deepcopy(model)
    personalized_models = {client_id: deepcopy(model) for client_id, _ in clients}
    global_losses: list[tuple[int, float]] = []
    personalized_losses: list[tuple[int, float]] = []
    checkpoints: list[DittoCheckpoint] = []
    derived_seeds: list[DataloaderShuffleSeed] = []

    for round_index in range(rounds):
        round_number = round_index + 1
        round_start = {name: tensor.detach().clone() for name, tensor in global_model.state_dict().items()}
        local_global_states: list[tuple[int, dict[str, torch.Tensor]]] = []
        for client_id, data in clients:
            epoch_seeds = tuple(
                derive_dataloader_shuffle_seed(
                    key=shuffle_seed_key,
                    digest_bytes=shuffle_seed_digest_bytes,
                    training_seed=seed,
                    round_number=round_number,
                    client_id=client_id,
                    local_epoch=local_epoch,
                )
                for local_epoch in range(max(local_epochs, personalized_local_epochs))
            )
            derived_seeds.extend(
                DataloaderShuffleSeed(
                    round_number=round_number,
                    client_id=client_id,
                    local_epoch=local_epoch,
                    value=epoch_seed,
                )
                for local_epoch, epoch_seed in enumerate(epoch_seeds)
            )
            global_local = train_autoencoder(
                deepcopy(global_model),
                data,
                local_epochs,
                learning_rate,
                batch_size,
                epoch_seeds[:local_epochs],
                device,
                beta_1,
                beta_2,
                epsilon,
                weight_decay,
                amsgrad,
                shuffle_each_epoch,
                None,
                None,
            )
            local_global_states.append((int(data.shape[0]), global_local.state_dict()))
            personalized_models[client_id] = train_autoencoder(
                personalized_models[client_id],
                data,
                personalized_local_epochs,
                learning_rate,
                batch_size,
                epoch_seeds[:personalized_local_epochs],
                device,
                beta_1,
                beta_2,
                epsilon,
                weight_decay,
                amsgrad,
                shuffle_each_epoch,
                round_start,
                proximal_weight,
            )
        global_model.load_state_dict(weighted_average_state(local_global_states))
        global_losses.append((round_number, weighted_reconstruction_loss(global_model, calibration_clients, device)))
        personalized_losses.append(
            (round_number, _weighted_personalized_reconstruction_loss(personalized_models, calibration_clients, device))
        )
        if round_number in checkpoint_rounds:
            checkpoints.append(
                DittoCheckpoint(
                    round_number=round_number,
                    global_state=_state_on_cpu(global_model),
                    personalized_states=tuple(
                        (client_id, _state_on_cpu(personalized_models[client_id])) for client_id, _ in clients
                    ),
                )
            )
    return DittoTrainingResult(
        global_model=global_model,
        personalized_models=tuple((client_id, personalized_models[client_id]) for client_id, _ in clients),
        global_round_losses=tuple(global_losses),
        personalized_round_losses=tuple(personalized_losses),
        scheduled_checkpoints=tuple(checkpoints),
        derived_shuffle_seeds=tuple(derived_seeds),
    )


def _state_on_cpu(model: nn.Module) -> tuple[tuple[str, torch.Tensor], ...]:
    return tuple((name, value.detach().cpu().clone()) for name, value in model.state_dict().items())


def _weighted_personalized_reconstruction_loss(
    personalized_models: dict[str, nn.Module],
    clients: tuple[tuple[str, torch.Tensor], ...],
    device: str,
) -> float:
    weighted_loss = 0.0
    total_rows = 0
    for client_id, data in clients:
        if client_id not in personalized_models:
            raise ValueError(f"Ditto personalized state is unavailable for client '{client_id}'")
        row_count = int(data.shape[0])
        weighted_loss += row_count * weighted_reconstruction_loss(
            personalized_models[client_id], ((client_id, data),), device
        )
        total_rows += row_count
    return weighted_loss / total_rows
