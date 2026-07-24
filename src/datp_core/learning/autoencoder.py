"""Dense autoencoder architecture, deterministic seeding, and device selection."""

from __future__ import annotations

import random

import numpy as np
import torch
import torch.nn as nn

from datp_core.core.hashing import derive_seed


def set_deterministic_seeds(seed: int) -> None:
    """Set deterministic random seeds across Python, NumPy, PyTorch CPU and CUDA."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def derive_model_initialization_seed(*, key: str, digest_bytes: int, training_seed: int) -> int:
    """Derive the configured model-initialization seed from its declared namespace."""
    return derive_seed(key, digest_bytes, (("training_seed", training_seed),))


def derive_dataloader_shuffle_seed(
    *,
    key: str,
    digest_bytes: int,
    training_seed: int,
    round_number: int,
    client_id: str,
    local_epoch: int,
) -> int:
    """Derive the configured per-client, per-round, per-local-epoch dataloader shuffle seed."""
    return derive_seed(
        key,
        digest_bytes,
        (
            ("client_identifier", client_id),
            ("local_epoch_index", local_epoch),
            ("round_index", round_number),
            ("training_seed", training_seed),
        ),
    )


def require_cuda_training_device() -> str:
    """Return CUDA only when available; scientific training may never silently fall back."""
    if not torch.cuda.is_available():
        raise ValueError("Configured CUDA-required training cannot run because no CUDA device is available")
    return "cuda"


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
