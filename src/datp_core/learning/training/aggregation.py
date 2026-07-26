"""Federated aggregation utilities: weighted averaging, validation, and reconstruction loss."""

from __future__ import annotations

import torch
from torch import nn


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
        raise ValueError(
            "Each federated client requires a non-empty two-dimensional training tensor")
    if tuple(client_id for client_id, _ in clients) != tuple(client_id for client_id, _ in calibration_clients):
        raise ValueError(
            "Each training client requires benign calibration rows for checkpoint selection")
    if any(data.ndim != 2 or data.shape[0] == 0 for _, data in calibration_clients):
        raise ValueError(
            "Each federated client requires non-empty two-dimensional calibration tensors")
    if any(round_number < 1 or round_number > rounds for round_number in checkpoint_rounds):
        raise ValueError("Scheduled checkpoint rounds must fall within the configured round budget")
    if len(set(checkpoint_rounds)) != len(checkpoint_rounds):
        raise ValueError("Scheduled checkpoint rounds must be unique")


def weighted_reconstruction_loss(model: nn.Module, clients: tuple[tuple[str, torch.Tensor], ...], device: str) -> float:
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
