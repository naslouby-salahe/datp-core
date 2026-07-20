"""PyTorch dense autoencoder training and reconstruction scoring infrastructure adapter."""

from __future__ import annotations

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset


class FixedDenseAutoencoder(nn.Module):
    """Fixed DATP dense autoencoder architecture: input -> [80, 40, 20] -> bottleneck -> [40, 80, input]."""

    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 80),
            nn.ReLU(),
            nn.Linear(80, 40),
            nn.ReLU(),
            nn.Linear(40, 20),
            nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(20, 40),
            nn.ReLU(),
            nn.Linear(40, 80),
            nn.ReLU(),
            nn.Linear(80, input_dim),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        return self.decoder(latent)


def train_autoencoder(
    model: FixedDenseAutoencoder,
    train_data: torch.Tensor,
    epochs: int = 1,
    learning_rate: float = 0.001,
    batch_size: int = 256,
    seed: int = 42,
    device: str = "cpu",
) -> FixedDenseAutoencoder:
    """Train the dense autoencoder deterministically."""
    torch.manual_seed(seed)
    model = model.to(device)
    model.train()

    dataset = TensorDataset(train_data)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.MSELoss(reduction="mean")

    for _ in range(epochs):
        for (batch_x,) in loader:
            batch_x = batch_x.to(device)
            optimizer.zero_grad()
            recon = model(batch_x)
            loss = criterion(recon, batch_x)
            loss.backward()
            optimizer.step()

    return model


def compute_reconstruction_scores(
    model: FixedDenseAutoencoder,
    data: torch.Tensor,
    batch_size: int = 256,
    device: str = "cpu",
) -> torch.Tensor:
    """Compute per-sample mean squared reconstruction error scores."""
    model = model.to(device)
    model.eval()
    dataset = TensorDataset(data)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=False)
    scores_list = []

    with torch.no_grad():
        for (batch_x,) in loader:
            batch_x = batch_x.to(device)
            recon = model(batch_x)
            # Per-row mean of squared feature error
            err = torch.mean((recon - batch_x) ** 2, dim=1)
            scores_list.append(err.cpu())

    return torch.cat(scores_list, dim=0)
