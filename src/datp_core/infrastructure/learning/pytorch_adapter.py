"""PyTorch dense autoencoder training, reconstruction scoring, and SafeTensors model persistence."""

from __future__ import annotations

import random
from collections.abc import Mapping
from copy import deepcopy
from hashlib import blake2b
from pathlib import Path

import numpy as np
import polars as pl
import torch
import torch.nn as nn
from attrs import define
from torch.utils.data import DataLoader, TensorDataset

_SCORE_IDENTITY_COLUMNS = ("source_path", "source_row_index", "client_id", "split", "is_attack")


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
    return _derive_seed(key, digest_bytes, (("training_seed", training_seed),))


def require_cuda_training_device() -> str:
    """Return CUDA only when available; scientific training may never silently fall back."""
    if not torch.cuda.is_available():
        raise ValueError("Configured CUDA-required training cannot run because no CUDA device is available")
    return "cuda"


def load_benign_client_tensors(
    path: Path, split: str, feature_columns: tuple[str, ...]
) -> tuple[tuple[str, torch.Tensor], ...]:
    """Load configured benign rows for one authorized split, ordered by client."""
    if not feature_columns:
        raise ValueError("Training requires configured model feature columns")
    frame = pl.read_parquet(path, columns=["split", "client_id", "is_attack", *feature_columns])
    required = {"split", "client_id", "is_attack", *feature_columns}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"Materialized payload lacks training columns: {', '.join(missing)}")
    selected = frame.filter((pl.col("split") == split) & ~pl.col("is_attack")).select("client_id", *feature_columns)
    if selected.is_empty():
        raise ValueError(f"Materialized payload has no benign {split} rows")
    tensors: list[tuple[str, torch.Tensor]] = []
    for client_id, client_rows in selected.group_by("client_id", maintain_order=True):
        values = client_rows.select(*feature_columns).to_numpy()
        if not np.isfinite(values).all():
            raise ValueError(f"Benign {split} rows for client '{client_id[0]}' contain non-finite feature values")
        tensors.append((str(client_id[0]), torch.tensor(values, dtype=torch.float32)))
    return tuple(sorted(tensors, key=lambda item: item[0]))


def score_materialized_split(
    model: nn.Module,
    path: Path,
    *,
    split: str,
    feature_columns: tuple[str, ...],
    batch_size: int,
    device: str,
) -> pl.DataFrame:
    """Score one materialized split while retaining its immutable row identity."""
    selected = _score_input_frame(path, split=split, feature_columns=feature_columns)
    values = selected.select(*feature_columns).to_numpy()
    scores = compute_reconstruction_scores(
        model,
        torch.tensor(values, dtype=torch.float32),
        batch_size=batch_size,
        device=device,
    ).numpy()
    return _score_output_frame(selected, scores)


def score_personalized_materialized_split(
    models: Mapping[str, nn.Module],
    path: Path,
    *,
    split: str,
    feature_columns: tuple[str, ...],
    batch_size: int,
    device: str,
) -> pl.DataFrame:
    """Score one split with the persistent Ditto state bound to each source client."""
    selected = _score_input_frame(path, split=split, feature_columns=feature_columns).with_row_index("_score_row")
    chunks: list[pl.DataFrame] = []
    for client, rows in selected.group_by("client_id", maintain_order=True):
        client_id = str(client[0])
        if client_id not in models:
            raise ValueError(f"Personalized checkpoint is unavailable for client '{client_id}'")
        scores = compute_reconstruction_scores(
            models[client_id],
            torch.tensor(rows.select(*feature_columns).to_numpy(), dtype=torch.float32),
            batch_size=batch_size,
            device=device,
        ).numpy()
        chunks.append(rows.with_columns(pl.Series("score", scores)))
    return _score_output_frame(pl.concat(chunks).sort("_score_row").drop("_score_row"), None)


def _score_input_frame(path: Path, *, split: str, feature_columns: tuple[str, ...]) -> pl.DataFrame:
    if split not in {"calibration", "test", "historical_calibration", "future_recalibration", "future_evaluation"}:
        raise ValueError(f"Scoring does not authorize split '{split}'")
    frame = pl.read_parquet(path, columns=[*_SCORE_IDENTITY_COLUMNS, *feature_columns])
    selected = frame.filter(pl.col("split") == split)
    if selected.is_empty():
        raise ValueError(f"Materialized payload has no {split} rows to score")
    if split in {"calibration", "historical_calibration", "future_recalibration"} and selected["is_attack"].any():
        raise ValueError("Calibration scoring must not include attack rows")
    if selected.select(pl.struct("source_path", "source_row_index").is_duplicated().any()).item():
        raise ValueError("Score input contains duplicate row identities")
    if not np.isfinite(selected.select(*feature_columns).to_numpy()).all():
        raise ValueError("Score input contains non-finite feature values")
    return selected


def _score_output_frame(selected: pl.DataFrame, scores: np.ndarray | None) -> pl.DataFrame:
    if scores is not None:
        selected = selected.with_columns(pl.Series("score", scores, dtype=pl.Float64))
    scores = selected["score"].to_numpy()
    if not np.isfinite(scores).all() or (scores < 0.0).any():
        raise ValueError("Model produced non-finite or negative reconstruction scores")
    return (
        selected.select(*_SCORE_IDENTITY_COLUMNS, "score")
        .with_columns(
            pl.col("score").cast(pl.Float64),
            pl.col("is_attack").cast(pl.Int64).alias("label"),
        )
        .drop("is_attack")
    )


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


@define(frozen=True, slots=True, kw_only=True)
class FederatedTrainingResult:
    model: nn.Module
    round_losses: tuple[tuple[int, float], ...]
    scheduled_checkpoints: tuple[FederatedCheckpoint, ...]
    derived_shuffle_seeds: tuple[DataloaderShuffleSeed, ...]


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
    _validate_federated_training_inputs(
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
                _derive_dataloader_shuffle_seed(
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
        global_model.load_state_dict(_weighted_average_state(local_models))
        round_number = round_index + 1
        losses.append((round_number, _weighted_reconstruction_loss(global_model, calibration_clients, device)))
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
    _validate_federated_training_inputs(
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
                _derive_dataloader_shuffle_seed(
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
        global_model.load_state_dict(_weighted_average_state(local_global_states))
        global_losses.append((round_number, _weighted_reconstruction_loss(global_model, calibration_clients, device)))
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


def _weighted_average_state(client_states: list[tuple[int, dict[str, torch.Tensor]]]) -> dict[str, torch.Tensor]:
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


def _validate_federated_training_inputs(
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


def _state_on_cpu(model: nn.Module) -> tuple[tuple[str, torch.Tensor], ...]:
    return tuple((name, value.detach().cpu().clone()) for name, value in model.state_dict().items())


def _weighted_reconstruction_loss(
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


def _weighted_personalized_reconstruction_loss(
    personalized_models: Mapping[str, nn.Module],
    clients: tuple[tuple[str, torch.Tensor], ...],
    device: str,
) -> float:
    weighted_loss = 0.0
    total_rows = 0
    for client_id, data in clients:
        if client_id not in personalized_models:
            raise ValueError(f"Ditto personalized state is unavailable for client '{client_id}'")
        row_count = int(data.shape[0])
        weighted_loss += row_count * _weighted_reconstruction_loss(
            personalized_models[client_id], ((client_id, data),), device
        )
        total_rows += row_count
    return weighted_loss / total_rows


def _derive_dataloader_shuffle_seed(
    *,
    key: str,
    digest_bytes: int,
    training_seed: int,
    round_number: int,
    client_id: str,
    local_epoch: int,
) -> int:
    return _derive_seed(
        key,
        digest_bytes,
        (
            ("client_identifier", client_id),
            ("local_epoch_index", local_epoch),
            ("round_index", round_number),
            ("training_seed", training_seed),
        ),
    )


def _derive_seed(key: str, digest_bytes: int, components: tuple[tuple[str, int | str], ...]) -> int:
    if not key or digest_bytes < 1:
        raise ValueError("Seed derivation requires a key and positive digest length")
    if tuple(name for name, _ in components) != tuple(sorted(name for name, _ in components)):
        raise ValueError("Seed derivation components must be ordered by ascending name")
    encoded = "|".join((key, *(f"{name}={value}" for name, value in components))).encode("utf-8")
    return int.from_bytes(blake2b(encoded, digest_size=digest_bytes).digest(), "big") % (2**32)


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
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle_each_epoch)
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
