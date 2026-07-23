"""FedAvg/FedProx federated training: the shared client-update-weighted aggregation loop.

`train_autoencoder` (the local per-client training step) and the three shared helpers
(`weighted_average_state`, `validate_federated_training_inputs`, `weighted_reconstruction_loss`)
are reused by `learning/personalization.py`'s Ditto training loop -- FedAvg is the core ladder
algorithm, so this module owns them; Ditto imports them from here rather than duplicating them.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

import torch
import torch.nn as nn
from attrs import define
from torch.utils.data import DataLoader, TensorDataset

from datp_core.learning.autoencoder import derive_dataloader_shuffle_seed, set_deterministic_seeds


@define(frozen=True, slots=True, kw_only=True)
class FederatedCheckpoint:
    round_number: int
    state: tuple[tuple[str, torch.Tensor], ...]


@define(frozen=True, slots=True, kw_only=True)
class DataloaderShuffleSeed:
    round_number: int
    client_id: str
    local_epoch: int
    value: int


@define(frozen=True, slots=True, kw_only=True)
class FederatedTrainingResult:
    model: nn.Module
    round_losses: tuple[tuple[int, float], ...]
    scheduled_checkpoints: tuple[FederatedCheckpoint, ...]
    derived_shuffle_seeds: tuple[DataloaderShuffleSeed, ...]


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


def weighted_average_state(client_states: list[tuple[int, dict[str, torch.Tensor]]]) -> dict[str, torch.Tensor]:
    total_rows = sum(row_count for row_count, _ in client_states)
    if total_rows < 1:
        raise ValueError("Federated aggregation requires positive client row counts")
    keys = tuple(client_states[0][1])
    if any(set(state) != set(keys) for _, state in client_states[1:]):
        raise ValueError("Federated aggregation requires identical model state keys")
    averaged: dict[str, torch.Tensor] = {}
    for key in keys:
        weighted = torch.zeros_like(client_states[0][1][key].detach().cpu())
        for row_count, state in client_states:
            weighted += row_count * state[key].detach().cpu()
        averaged[key] = weighted / total_rows
    return averaged


def validate_federated_training_inputs(
    client_training_data: tuple[tuple[str, torch.Tensor], ...],
    client_calibration_data: tuple[tuple[str, torch.Tensor], ...],
    *,
    rounds: int,
    local_epochs: int,
    checkpoint_rounds: tuple[int, ...],
) -> None:
    if rounds < 1 or local_epochs < 1:
        raise ValueError("Federated training requires positive rounds and local epochs")
    clients = tuple(sorted(client_training_data, key=lambda item: item[0]))
    calibration_clients = tuple(sorted(client_calibration_data, key=lambda item: item[0]))
    if not clients:
        raise ValueError("Federated training requires at least one client")
    if len({client_id for client_id, _ in clients}) != len(clients):
        raise ValueError("Federated training requires unique client identifiers")
    if any(data.ndim != 2 or data.shape[0] == 0 for _, data in clients):
        raise ValueError("Each federated client requires a non-empty two-dimensional training tensor")
    if tuple(client_id for client_id, _ in clients) != tuple(client_id for client_id, _ in calibration_clients):
        raise ValueError("Each training client requires benign calibration rows for checkpoint selection")
    if any(data.ndim != 2 or data.shape[0] == 0 for _, data in calibration_clients):
        raise ValueError("Each federated client requires non-empty two-dimensional calibration tensors")
    if any(round_number < 1 or round_number > rounds for round_number in checkpoint_rounds):
        raise ValueError("Scheduled checkpoint rounds must fall within the configured round budget")
    if len(set(checkpoint_rounds)) != len(checkpoint_rounds):
        raise ValueError("Scheduled checkpoint rounds must be unique")


def weighted_reconstruction_loss(
    model: nn.Module, clients: tuple[tuple[str, torch.Tensor], ...], device: str
) -> float:
    model = model.to(device)
    model.eval()
    weighted_loss = 0.0
    total_rows = 0
    with torch.no_grad():
        for _, data in clients:
            batch = data.to(device)
            loss = torch.mean((model(batch) - batch) ** 2).item()
            row_count = int(data.shape[0])
            weighted_loss += row_count * loss
            total_rows += row_count
    return weighted_loss / total_rows


def fedprox_objective(
    reconstruction_loss: torch.Tensor,
    model: nn.Module,
    global_round_start_state: Mapping[str, torch.Tensor],
    proximal_mu: float,
) -> torch.Tensor:
    """Return the genuine FedProx local objective against the round-start global state."""
    if proximal_mu <= 0.0:
        raise ValueError("FedProx requires a strictly positive proximal coefficient")
    model_state = model.state_dict()
    if set(model_state) != set(global_round_start_state):
        raise ValueError("FedProx reference state must exactly match the local model state")
    penalty = sum(
        torch.sum((parameter - global_round_start_state[name].to(parameter.device)) ** 2)
        for name, parameter in model.named_parameters()
    )
    return reconstruction_loss + ((proximal_mu / 2.0) * penalty)


def train_autoencoder(
    model: nn.Module,
    train_data: torch.Tensor,
    epochs: int,
    learning_rate: float,
    batch_size: int,
    epoch_seeds: tuple[int, ...],
    device: str,
    beta_1: float,
    beta_2: float,
    epsilon: float,
    weight_decay: float,
    amsgrad: bool,
    shuffle_each_epoch: bool,
    global_round_start_state: Mapping[str, torch.Tensor] | None,
    proximal_mu: float | None,
) -> nn.Module:
    """Train the dense autoencoder deterministically with explicit seeds and config parameters."""
    if len(epoch_seeds) != epochs:
        raise ValueError("Training requires one dataloader shuffle seed per local epoch")
    model = model.to(device)
    model.train()

    dataset = TensorDataset(train_data)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
        betas=(beta_1, beta_2),
        eps=epsilon,
        weight_decay=weight_decay,
        amsgrad=amsgrad,
    )
    criterion = nn.MSELoss(reduction="mean")
    if (global_round_start_state is None) != (proximal_mu is None):
        raise ValueError("FedProx state and coefficient must be provided together")

    for epoch_seed in epoch_seeds:
        set_deterministic_seeds(epoch_seed)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle_each_epoch, num_workers=0)
        for (batch_x,) in loader:
            batch_x = batch_x.to(device)
            optimizer.zero_grad()
            recon = model(batch_x)
            loss = criterion(recon, batch_x)
            if global_round_start_state is not None and proximal_mu is not None:
                loss = fedprox_objective(loss, model, global_round_start_state, proximal_mu)
            loss.backward()
            optimizer.step()

    return model
