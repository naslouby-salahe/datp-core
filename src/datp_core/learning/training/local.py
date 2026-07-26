"""Local per-client training step (FedProx objective + train_autoencoder)."""

from __future__ import annotations

from collections.abc import Mapping

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.learning.model.determinism import set_deterministic_seeds


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
