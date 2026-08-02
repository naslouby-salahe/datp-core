"""Shared client-local training mechanics reused by FedAvg, FedProx, and Ditto."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256

import numpy as np
import polars as pl
import torch
from safetensors.torch import save
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.domain.enums import ContractSubject, ProcessedDataBranch
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureNameSequence,
    LearningRate,
    MetricValue,
    OutcomeLabelSequence,
    ProximalCoefficient,
    RowCount,
    Seed,
)
from datp_core.learning.autoencoder import ReconstructionAutoencoder
from datp_core.learning.federated.models import ClientUpdate
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN
from datp_core.preprocessing.models import FittedPreprocessingState
from datp_core.protocols.models import OptimizerProtocol
from datp_core.protocols.training import FEDERATED_DATALOADER_WORKER_COUNT
from datp_core.runtime.compute import require_cuda_available
from datp_core.runtime.determinism import derive_worker_seed


def reject_centralized_preprocessing_for_federated_training(state: FittedPreprocessingState) -> None:
    if state.branch is not ProcessedDataBranch.FEDERATED:
        raise LeakageError(
            "centralized preprocessing state cannot enter federated training",
            subject=state.branch,
        )
    if state.client_identity is None:
        raise LeakageError(
            "federated training requires client-scoped preprocessing state",
            subject=ContractSubject.CLIENT_IDENTITY,
        )


def reject_attack_rows_in_federated_training(labels: OutcomeLabelSequence, benign_label: str) -> None:
    if any(label != benign_label for label in labels):
        raise LeakageError(
            "attack-labelled rows cannot enter federated benign training",
            subject=ContractSubject.LABEL,
        )


def extract_feature_arrays(
    frame: pl.DataFrame,
    feature_names: FeatureNameSequence,
) -> tuple[np.ndarray, OutcomeLabelSequence, tuple[str, ...]]:
    labels = OutcomeLabelSequence(tuple(str(value) for value in frame.get_column(OUTCOME_LABEL_COLUMN).to_list()))
    row_ids = tuple(str(value) for value in frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    matrix = frame.select(feature_names.as_list()).to_numpy().astype(np.float32, copy=False)
    if not np.isfinite(matrix).all():
        raise ScientificContractError("federated features must be finite", subject=ContractSubject.FEATURES)
    if len(labels) != matrix.shape[0] or len(row_ids) != matrix.shape[0]:
        raise ScientificContractError("federated arrays must align by row", subject=ContractSubject.ROWS)
    return matrix, labels, row_ids


def client_round_seed(training_seed: Seed, client_index: int) -> Seed:
    """Deterministic per-client, collision-free seed derived from the training seed."""
    return derive_worker_seed(training_seed, client_index)


def build_client_loader(
    matrix: np.ndarray,
    *,
    batch_size: BatchSize,
    seed: Seed,
    device: torch.device,
) -> DataLoader:
    # DataLoader shuffle generators must live on CPU; model tensors remain on CUDA.
    require_cuda_available()
    tensor = torch.tensor(np.asarray(matrix, dtype=np.float32), dtype=torch.float32, device=device)
    dataset = TensorDataset(tensor)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed.value)
    return DataLoader(
        dataset,
        batch_size=batch_size.value,
        shuffle=True,
        drop_last=True,
        generator=generator,
        num_workers=FEDERATED_DATALOADER_WORKER_COUNT.value,
    )


def proximal_penalty(
    local_parameters: Sequence[torch.Tensor],
    reference_parameters: Sequence[torch.Tensor],
    coefficient: ProximalCoefficient,
) -> torch.Tensor:
    """The proximal term (coefficient / 2) * sum ||local - reference||^2."""
    total = torch.zeros((), device=local_parameters[0].device)
    for local, reference in zip(local_parameters, reference_parameters, strict=True):
        total = total + torch.sum((local - reference) ** 2)
    return (coefficient.value / 2.0) * total


def build_optimizer(
    model: ReconstructionAutoencoder,
    optimizer_protocol: OptimizerProtocol,
    learning_rate: LearningRate,
) -> torch.optim.Optimizer:
    from datp_core.domain.enums import OptimizerId

    match optimizer_protocol.identity:
        case OptimizerId.ADAM:
            return torch.optim.Adam(
                model.parameters(),
                lr=learning_rate.value,
                weight_decay=optimizer_protocol.weight_decay.value,
            )


@dataclass(frozen=True, slots=True)
class ProximalTerm:
    """A fixed reference state and coefficient for a proximal penalty toward that state."""

    reference_state: Mapping[str, torch.Tensor]
    coefficient: ProximalCoefficient  # WAS: float


def run_local_epoch(
    model: ReconstructionAutoencoder,
    optimizer: torch.optim.Optimizer,
    loader: DataLoader,
    device: torch.device,
    *,
    proximal_term: ProximalTerm | None = None,
) -> tuple[dict[str, torch.Tensor], MetricValue, RowCount]:
    """Run exactly one local training epoch and return the resulting CPU state dict."""
    reference_parameters = _resolve_reference_parameters(model, proximal_term, device)
    model.train()
    batch_losses: list[float] = []
    sample_count = 0
    for (batch,) in loader:
        batch = batch.to(device, non_blocking=False)
        batch_loss = _train_one_batch(model, optimizer, batch, reference_parameters, proximal_term)
        batch_losses.append(batch_loss)
        sample_count += batch.shape[0]
    if not batch_losses:
        raise ScientificContractError(
            "federated local training produced no batches; declared batch size cannot be relaxed",
            subject=ContractSubject.BATCH_SIZE,
        )
    mean_loss = MetricValue(float(np.mean(np.asarray(batch_losses, dtype=float))))
    state = {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}
    return state, mean_loss, RowCount(sample_count)


def _resolve_reference_parameters(
    model: ReconstructionAutoencoder,
    proximal_term: ProximalTerm | None,
    device: torch.device,
) -> tuple[torch.Tensor, ...] | None:
    if proximal_term is None:
        return None
    return tuple(proximal_term.reference_state[name].detach().to(device) for name, _ in model.named_parameters())


def _train_one_batch(
    model: ReconstructionAutoencoder,
    optimizer: torch.optim.Optimizer,
    batch: torch.Tensor,
    reference_parameters: tuple[torch.Tensor, ...] | None,
    proximal_term: ProximalTerm | None,
) -> float:
    optimizer.zero_grad(set_to_none=True)
    reconstruction = model(batch)
    loss = nn.functional.mse_loss(reconstruction, batch)
    if reference_parameters is not None and proximal_term is not None:
        local_parameters = tuple(parameter for _, parameter in model.named_parameters())
        loss = loss + proximal_penalty(local_parameters, reference_parameters, proximal_term.coefficient)
    loss.backward()
    optimizer.step()
    return float(loss.detach().cpu().item())


def aggregate_client_updates(updates: Sequence[ClientUpdate]) -> dict[str, torch.Tensor]:
    """Sample-count-weighted average of client parameters (McMahan FedAvg aggregation)."""
    if not updates:
        raise ScientificContractError(
            "aggregation requires at least one client update",
            subject=ContractSubject.CLIENT,
        )
    total_samples = sum(update.sample_count.value for update in updates)
    if total_samples < 1:
        raise ScientificContractError(
            "aggregation requires a positive total sample count",
            subject=ContractSubject.ROWS,
        )
    reference_keys = tuple(updates[0].state_dict.keys())
    aggregated: dict[str, torch.Tensor] = {}
    for key in reference_keys:
        weighted_sum = torch.zeros_like(updates[0].state_dict[key], dtype=torch.float64)
        for update in updates:
            weight = update.sample_count.value / total_samples
            weighted_sum = weighted_sum + update.state_dict[key].to(torch.float64) * weight
        aggregated[key] = weighted_sum.to(updates[0].state_dict[key].dtype)
    return aggregated


def preprocessing_state_set_checksum(checksums: Sequence[Checksum]) -> Checksum:
    """One deterministic checksum over every client's independently fitted preprocessing state."""
    ordered = sorted(item.value for item in checksums)
    return Checksum(sha256("|".join(ordered).encode()).hexdigest())


def serialized_state_dict_bytes(state_dict: Mapping[str, torch.Tensor]) -> bytes:
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    return save(cpu_state)


def checksum_state_dict(state_dict: Mapping[str, torch.Tensor]) -> Checksum:
    return Checksum(sha256(serialized_state_dict_bytes(state_dict)).hexdigest())
