"""Shared client-local training mechanics reused by FedAvg, FedProx, and Ditto."""

from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256

import numpy as np
import polars as pl
import torch
from safetensors.torch import save
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.domain.enums import ContractSubject, OptimizerId, ProcessedDataBranch
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    DittoRegularization,
    FeatureNameSequence,
    LearningRate,
    MetricValue,
    ModelStateMap,
    OutcomeLabelSequence,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    Seed,
)
from datp_core.learning.autoencoder import ReconstructionAutoencoder
from datp_core.learning.federated.models import ClientTrainingInput, ClientUpdate
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ClientIdentity,
    PopulationOutcomeLabel,
)
from datp_core.preprocessing.models import FittedPreprocessingState
from datp_core.protocols.models import OptimizerProtocol
from datp_core.protocols.training import FEDERATED_DATALOADER_WORKER_COUNT
from datp_core.runtime.compute import require_cuda_available
from datp_core.runtime.determinism import derive_worker_seed


@dataclass(frozen=True, slots=True)
class PreparedFederatedClientData:
    client: ClientIdentity
    features_cpu: torch.Tensor
    sample_count: RowCount
    preprocessing_state: FittedPreprocessingState


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


def reject_attack_rows_in_federated_training(
    labels: OutcomeLabelSequence | Sequence[str],
    benign_label: PopulationOutcomeLabel | str = PopulationOutcomeLabel.BENIGN,
) -> None:
    target_value = benign_label.value if isinstance(benign_label, PopulationOutcomeLabel) else str(benign_label)
    if any(label != target_value for label in labels):
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


def prepare_federated_client_data(
    client_input: ClientTrainingInput,
    preprocessing_state: FittedPreprocessingState,
    *,
    benign_label: PopulationOutcomeLabel = PopulationOutcomeLabel.BENIGN,
) -> PreparedFederatedClientData:
    """Validate client data once before round loop and store complete CPU tensors."""
    reject_centralized_preprocessing_for_federated_training(preprocessing_state)
    matrix, labels, _row_ids = extract_feature_arrays(
        client_input.training_features,
        client_input.feature_names,
    )
    reject_attack_rows_in_federated_training(labels, benign_label)
    features_cpu = torch.tensor(matrix, dtype=torch.float32, device="cpu")
    return PreparedFederatedClientData(
        client=client_input.client,
        features_cpu=features_cpu,
        sample_count=RowCount(matrix.shape[0]),
        preprocessing_state=preprocessing_state,
    )


def client_round_seed(
    training_seed: Seed,
    round_number_or_client_index: RoundNumber | int,
    client_index: int | None = None,
) -> Seed:
    """Deterministic per-round per-client seed derived from training seed."""
    if client_index is None:
        client_idx = (
            round_number_or_client_index.value
            if isinstance(round_number_or_client_index, RoundNumber)
            else round_number_or_client_index
        )
        round_val = 1
    else:
        client_idx = client_index
        round_val = (
            round_number_or_client_index.value
            if isinstance(round_number_or_client_index, RoundNumber)
            else round_number_or_client_index
        )
    round_seed = derive_worker_seed(training_seed, round_val)
    return derive_worker_seed(round_seed, client_idx)


def build_client_loader(
    data: PreparedFederatedClientData | np.ndarray | pl.DataFrame,
    *,
    batch_size: BatchSize,
    seed: Seed,
    device: torch.device | None = None,
) -> DataLoader:
    """Build a CPU DataLoader for federated client training batches."""
    if isinstance(data, PreparedFederatedClientData):
        features_cpu = data.features_cpu
    elif isinstance(data, pl.DataFrame):
        features_cpu = torch.tensor(
            data.select(pl.all().exclude([STABLE_ROW_ID_COLUMN, OUTCOME_LABEL_COLUMN])).to_numpy(),
            dtype=torch.float32,
            device="cpu",
        )
    else:
        features_cpu = torch.tensor(data, dtype=torch.float32, device="cpu")

    if features_cpu.shape[0] == 0:
        raise ScientificContractError(
            "federated local training produced no batches; declared batch size cannot be relaxed",
            subject=ContractSubject.BATCH_SIZE,
        )

    dataset = TensorDataset(features_cpu)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed.value)
    return DataLoader(
        dataset,
        batch_size=batch_size.value,
        shuffle=True,
        drop_last=False,
        generator=generator,
        num_workers=FEDERATED_DATALOADER_WORKER_COUNT.value,
    )


def proximal_penalty(
    local_parameters: Sequence[torch.Tensor],
    reference_parameters: Sequence[torch.Tensor],
    coefficient: ProximalCoefficient | DittoRegularization,
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
    match optimizer_protocol.identity:
        case OptimizerId.ADAM:
            return torch.optim.Adam(
                model.parameters(),
                lr=learning_rate.value,
                weight_decay=optimizer_protocol.weight_decay.value,
            )
        case _:
            raise ScientificContractError(
                f"unsupported optimizer {optimizer_protocol.identity}",
                subject=ContractSubject.OPTIMIZER,
            )


@dataclass(frozen=True, slots=True)
class ProximalTerm:
    """A fixed reference state and coefficient for a proximal penalty toward that state."""

    reference_state: ModelStateMap
    coefficient: ProximalCoefficient | DittoRegularization


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
    accumulated_weighted_loss = 0.0
    total_samples = 0
    batch_count = 0
    for (batch,) in loader:
        batch_samples = batch.shape[0]
        batch = batch.to(device, non_blocking=False)
        batch_loss = _train_one_batch(model, optimizer, batch, reference_parameters, proximal_term)
        accumulated_weighted_loss += batch_loss * batch_samples
        total_samples += batch_samples
        batch_count += 1
    if batch_count == 0 or total_samples == 0:
        raise ScientificContractError(
            "federated local training produced no batches; declared batch size cannot be relaxed",
            subject=ContractSubject.BATCH_SIZE,
        )
    mean_loss = MetricValue(accumulated_weighted_loss / total_samples)
    state = {name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()}
    return state, mean_loss, RowCount(total_samples)


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
    for update in updates:
        if tuple(update.state_dict.keys()) != reference_keys:
            raise ScientificContractError(
                "parameter key mismatch during aggregation",
                subject=ContractSubject.TRAINING,
            )
        for key in reference_keys:
            t1 = updates[0].state_dict[key]
            t2 = update.state_dict[key]
            if t1.shape != t2.shape or t1.dtype != t2.dtype:
                raise ScientificContractError(
                    "parameter shape or dtype mismatch during aggregation",
                    subject=ContractSubject.TRAINING,
                )
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


def serialized_state_dict_bytes(state_dict: ModelStateMap) -> bytes:
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    return save(cpu_state)


def checksum_state_dict(state_dict: ModelStateMap) -> Checksum:
    return Checksum(sha256(serialized_state_dict_bytes(state_dict)).hexdigest())
