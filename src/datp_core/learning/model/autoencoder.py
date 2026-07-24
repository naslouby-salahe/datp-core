"""Dense autoencoder architecture built from ModelArchitectureConfig."""

from __future__ import annotations

import torch
import torch.nn as nn


class DynamicDenseAutoencoder(nn.Module):
    """Dynamic dense autoencoder architecture built from ModelArchitectureConfig."""

    def __init__(self, input_dim: int, hidden_dims: tuple[int, ...]) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_dims = hidden_dims

        encoder_layers: list[nn.Module] = []
        in_d = input_dim
        for h_d in hidden_dims:
            encoder_layers.append(nn.Linear(in_d, h_d))
            encoder_layers.append(nn.ReLU())
            in_d = h_d
        self.encoder = nn.Sequential(*encoder_layers)

        decoder_layers: list[nn.Module] = []
        rev_dims = list(reversed(hidden_dims[:-1])) + [input_dim]
        in_d = hidden_dims[-1]
        for idx, out_d in enumerate(rev_dims):
            decoder_layers.append(nn.Linear(in_d, out_d))
            if idx < len(rev_dims) - 1:
                decoder_layers.append(nn.ReLU())
            in_d = out_d
        self.decoder = nn.Sequential(*decoder_layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        return self.decoder(latent)
