"""PyTorch dense autoencoder training, reconstruction scoring, and SafeTensors model persistence."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.domain.artifacts import ArtifactCommitResult, ArtifactKey, ArtifactParent
from datp_core.domain.fingerprints import Fingerprint
from datp_core.domain.identifiers import ExperimentId
from datp_core.domain.values import Seed
from datp_core.infrastructure.artifacts.model_store import (
    load_model_safetensors as _load_state_dict_safetensors,
)
from datp_core.infrastructure.artifacts.model_store import (
    save_model_safetensors as _save_state_dict_safetensors,
)


def set_deterministic_seeds(seed: int) -> None:
    """Set deterministic random seeds across Python, NumPy, PyTorch CPU and CUDA."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


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


def save_model_safetensors(
    model: nn.Module,
    *,
    outputs_dir: Path,
    artifact_key: ArtifactKey,
    scientific_fingerprint: Fingerprint,
    execution_fingerprint: Fingerprint,
    relative_path: str,
    schema_version: int,
    creation_timestamp: float,
    environment_identity: str,
    lock_timeout: float,
    parents: tuple[ArtifactParent, ...] = (),
    experiment_id: ExperimentId | None = None,
    seed: Seed | None = None,
) -> ArtifactCommitResult:
    """Persist PyTorch model weights as a SafeTensors artifact via the atomic model store."""
    return _save_state_dict_safetensors(
        model.state_dict(),
        outputs_dir=outputs_dir,
        artifact_key=artifact_key,
        scientific_fingerprint=scientific_fingerprint,
        execution_fingerprint=execution_fingerprint,
        relative_path=relative_path,
        schema_version=schema_version,
        creation_timestamp=creation_timestamp,
        environment_identity=environment_identity,
        lock_timeout=lock_timeout,
        parents=parents,
        experiment_id=experiment_id,
        seed=seed,
    )


def load_model_safetensors(model: nn.Module, relative_path: str, outputs_dir: Path) -> nn.Module:
    """Load PyTorch model weights from a committed, checksum-verified SafeTensors artifact."""
    model.load_state_dict(_load_state_dict_safetensors(relative_path, outputs_dir))
    return model


def train_autoencoder(
    model: nn.Module,
    train_data: torch.Tensor,
    epochs: int,
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
) -> nn.Module:
    """Train the dense autoencoder deterministically with explicit seeds and config parameters."""
    set_deterministic_seeds(seed)
    model = model.to(device)
    model.train()

    dataset = TensorDataset(train_data)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle_each_epoch)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=learning_rate,
        betas=(beta_1, beta_2),
        eps=epsilon,
        weight_decay=weight_decay,
        amsgrad=amsgrad,
    )
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
    model: nn.Module,
    data: torch.Tensor,
    batch_size: int,
    device: str,
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
            err = torch.mean((recon - batch_x) ** 2, dim=1)
            scores_list.append(err.cpu())

    return torch.cat(scores_list, dim=0)
