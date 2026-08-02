"""Shared client-local training mechanics reused by FedAvg, FedProx, and Ditto."""

from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from hashlib import sha256
from pathlib import Path

import numpy as np
import torch
from safetensors.torch import save
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.domain.enums import (
    CommunicationEstimationMethod,
    ContractSubject,
    OptimizerId,
)
from datp_core.domain.errors import LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    ByteCount,
    Checksum,
    ClientCount,
    DittoRegularization,
    LearningRate,
    MetricValue,
    OutcomeLabelSequence,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    Seed,
)
from datp_core.learning.autoencoder import (
    LEARNING_DTYPE,
    TORCH_LEARNING_DTYPE,
    AutoencoderState,
    ReconstructionAutoencoder,
    build_reconstruction_autoencoder,
    clone_autoencoder_state,
    clone_state,
    load_autoencoder_state,
)
from datp_core.learning.federated.checkpointing import retain_checkpoint_candidates
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    ClientTrainingResult,
    ClientUpdate,
    CommunicationRecord,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingHistory,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
    GlobalModelStateReference,
    RoundSnapshot,
)
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    ClientIdentity,
    PopulationOutcomeLabel,
)
from datp_core.protocols.models import (
    AutoencoderProtocol,
    CheckpointProtocol,
    FedAvgProtocol,
    FedProxProtocol,
    OptimizerProtocol,
)
from datp_core.protocols.training import FEDERATED_DATALOADER_WORKER_COUNT
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.runtime.determinism import configure_deterministic_execution, derive_worker_seed


class TrainingStream(IntEnum):
    GLOBAL_CLIENT_UPDATE = 0
    PERSONALIZED_CLIENT_UPDATE = 1


@dataclass(frozen=True, slots=True)
class PreparedFederatedClientData:
    client: ClientIdentity
    features_cpu: torch.Tensor
    preprocessing_checksum: Checksum

    def __post_init__(self) -> None:
        if self.features_cpu.dim() != 2:
            raise ScientificContractError(
                "prepared features tensor must be two-dimensional",
                subject=ContractSubject.FEATURES,
            )
        if self.features_cpu.device.type != "cpu":
            raise ScientificContractError(
                "prepared features must reside on CPU",
                subject=ContractSubject.RUNTIME,
            )
        if self.features_cpu.dtype != TORCH_LEARNING_DTYPE:
            raise ScientificContractError(
                "prepared features must use the canonical torch learning dtype",
                subject=ContractSubject.FEATURES,
            )
        if self.features_cpu.shape[0] < 1:
            raise ScientificContractError(
                "prepared client data requires at least one row",
                subject=ContractSubject.ROWS,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingRequest[T: (FedAvgProtocol, FedProxProtocol)]:
    coordinate: FederatedTrainingCoordinate
    clients: tuple[ClientTrainingInput, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: T
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path


def reject_attack_rows_in_federated_training(labels: OutcomeLabelSequence) -> None:
    if any(label != PopulationOutcomeLabel.BENIGN.value for label in labels):
        raise LeakageError(
            "attack-labelled rows cannot enter federated benign training",
            subject=ContractSubject.LABEL,
        )


def prepare_federated_client_data(
    client_input: ClientTrainingInput,
    autoencoder: AutoencoderProtocol,
) -> PreparedFederatedClientData:
    labels = OutcomeLabelSequence(
        tuple(str(value) for value in client_input.training_features.get_column(OUTCOME_LABEL_COLUMN).to_list())
    )
    reject_attack_rows_in_federated_training(labels)

    matrix = (
        client_input.training_features.select(client_input.feature_names.as_list())
        .to_numpy()
        .astype(LEARNING_DTYPE, copy=False)
    )
    if not np.isfinite(matrix).all():
        raise ScientificContractError("federated features must be finite", subject=ContractSubject.FEATURES)
    if matrix.shape[1] != autoencoder.widths[0]:
        raise ScientificContractError(
            "feature width mismatch during dataset preparation", subject=ContractSubject.FEATURES
        )
    if len(labels) != matrix.shape[0]:
        raise ScientificContractError("federated arrays must align by row", subject=ContractSubject.ROWS)

    features_cpu = torch.tensor(matrix, dtype=TORCH_LEARNING_DTYPE, device="cpu")
    return PreparedFederatedClientData(
        client=client_input.client,
        features_cpu=features_cpu,
        preprocessing_checksum=client_input.preprocessing_state.estimator_checksum,
    )


def derive_client_stream_seed(
    training_seed: Seed,
    round_number: RoundNumber,
    client_index: int,
    stream: TrainingStream,
) -> Seed:
    round_seed = derive_worker_seed(training_seed, round_number.value)
    client_seed = derive_worker_seed(round_seed, client_index)
    return derive_worker_seed(client_seed, stream.value)


def build_client_loader(
    data: PreparedFederatedClientData,
    *,
    batch_size: BatchSize,
    seed: Seed,
) -> DataLoader:
    dataset = TensorDataset(data.features_cpu)
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
    reference_state: AutoencoderState
    coefficient: ProximalCoefficient | DittoRegularization


def run_local_epoch(
    model: ReconstructionAutoencoder,
    optimizer: torch.optim.Optimizer,
    loader: DataLoader,
    device: torch.device,
    *,
    proximal_term: ProximalTerm | None = None,
) -> tuple[AutoencoderState, MetricValue, RowCount]:
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
    state = clone_state(dict(model.state_dict()))
    return state, mean_loss, RowCount(total_samples)


def train_client_update(
    client_data: PreparedFederatedClientData,
    initial_state: AutoencoderState,
    autoencoder: AutoencoderProtocol,
    optimizer_protocol: OptimizerProtocol,
    learning_rate: LearningRate,
    batch_size: BatchSize,
    seed: Seed,
    device: torch.device,
    *,
    proximal_term: ProximalTerm | None = None,
) -> tuple[ClientUpdate, ClientTrainingResult]:
    local_model = ReconstructionAutoencoder(autoencoder.widths).to(device)
    load_autoencoder_state(local_model, initial_state)
    optimizer = build_optimizer(local_model, optimizer_protocol, learning_rate)
    loader = build_client_loader(client_data, batch_size=batch_size, seed=seed)
    local_state, local_loss, sample_count = run_local_epoch(
        local_model, optimizer, loader, device, proximal_term=proximal_term
    )
    client = client_data.client
    update = ClientUpdate(client=client, state_dict=local_state, sample_count=sample_count, local_loss=local_loss)
    result = ClientTrainingResult(client=client, sample_count=sample_count, local_loss=local_loss)
    return update, result


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


def aggregate_client_updates(updates: Sequence[ClientUpdate]) -> AutoencoderState:
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
    aggregated: AutoencoderState = {}
    for key in reference_keys:
        weighted_sum = torch.zeros_like(updates[0].state_dict[key], dtype=torch.float64)
        for update in updates:
            weight = update.sample_count.value / total_samples
            weighted_sum = weighted_sum + update.state_dict[key].to(torch.float64) * weight
        aggregated[key] = weighted_sum.to(updates[0].state_dict[key].dtype)
    return aggregated


def preprocessing_state_set_checksum(
    client_checksum_pairs: Sequence[tuple[ClientIdentity, Checksum]],
) -> Checksum:
    entries = sorted(f"{client.client_id}:{checksum.value}" for client, checksum in client_checksum_pairs)
    return Checksum(sha256("|".join(entries).encode()).hexdigest())


def serialize_and_checksum_state_dict(
    state_dict: AutoencoderState,
) -> tuple[Checksum, ByteCount]:
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    payload = save(cpu_state)
    checksum = Checksum(sha256(payload).hexdigest())
    byte_count = ByteCount(len(payload))
    return checksum, byte_count


def validate_common_request(
    clients: tuple[ClientTrainingInput, ...],
    population_client_count: ClientCount,
) -> None:
    if not clients:
        raise ScientificContractError(
            "training requires at least one client dataset",
            subject=ContractSubject.CLIENT,
        )
    client_ids = tuple(item.client.client_id for item in clients)
    if len(set(client_ids)) != len(client_ids):
        raise ScientificContractError(
            "training cannot receive duplicate client identities",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if len(clients) != population_client_count.value:
        raise ScientificContractError(
            "training requires exactly the declared population client count",
            subject=ContractSubject.CLIENT,
        )


def compute_weighted_aggregate_loss(updates: Sequence[ClientUpdate]) -> MetricValue:
    if not updates:
        raise ScientificContractError(
            "aggregate loss requires at least one client update",
            subject=ContractSubject.CLIENT,
        )
    total_samples = sum(u.sample_count.value for u in updates)
    return MetricValue(sum(u.local_loss.value * u.sample_count.value for u in updates) / total_samples)


def create_communication_record(
    round_number: RoundNumber,
    state_bytes: ByteCount,
    upload_count: int,
    download_count: int,
) -> CommunicationRecord:
    return CommunicationRecord(
        round_number=round_number,
        estimated_upload_bytes=ByteCount(upload_count * state_bytes.value),
        estimated_download_bytes=ByteCount(download_count * state_bytes.value),
        estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
    )


def create_round_snapshot(
    round_number: RoundNumber,
    state: AutoencoderState,
    loss: MetricValue,
) -> RoundSnapshot:
    return RoundSnapshot(round_number, clone_state(state), loss)


def run_federated_training(
    request: FederatedTrainingRequest,
) -> FederatedTrainingOutcome:
    validate_common_request(request.clients, request.population_client_count)
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()

    ordered_clients = tuple(sorted(request.clients, key=lambda item: item.client))
    prepared_clients: list[PreparedFederatedClientData] = [
        prepare_federated_client_data(client_input, request.autoencoder) for client_input in ordered_clients
    ]

    global_model = build_reconstruction_autoencoder(request.autoencoder, initialization_seed=request.training_seed)
    global_state = clone_autoencoder_state(global_model)
    global_model.to(device)
    del global_model

    candidate_rounds: set[RoundNumber] = set(request.checkpoint_protocol.candidates)
    proximal_coefficient = _resolve_proximal_coefficient(request.training_protocol)
    rounds: list[FederatedRoundResult] = []
    snapshots: list[RoundSnapshot] = []

    for round_index in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_index)
        client_updates: list[ClientUpdate] = []
        client_results: list[ClientTrainingResult] = []
        reference_state = {name: tensor.to(device) for name, tensor in global_state.items()}

        for client_index, client_data in enumerate(prepared_clients):
            client_seed = derive_client_stream_seed(
                request.training_seed, round_number, client_index, TrainingStream.GLOBAL_CLIENT_UPDATE
            )
            proximal_term = (
                ProximalTerm(reference_state=reference_state, coefficient=proximal_coefficient)
                if proximal_coefficient is not None
                else None
            )
            update, result = train_client_update(
                client_data=client_data,
                initial_state=reference_state,
                autoencoder=request.autoencoder,
                optimizer_protocol=request.training_protocol.optimizer,
                learning_rate=request.learning_rate,
                batch_size=request.batch_size,
                seed=client_seed,
                device=device,
                proximal_term=proximal_term,
            )
            client_updates.append(update)
            client_results.append(result)

        aggregated = aggregate_client_updates(client_updates)
        global_state = aggregated

        aggregate_loss = compute_weighted_aggregate_loss(client_updates)
        state_checksum, single_state_bytes = serialize_and_checksum_state_dict(aggregated)

        client_count = len(ordered_clients)
        communication = create_communication_record(round_number, single_state_bytes, client_count, client_count)
        global_reference = GlobalModelStateReference(
            coordinate=request.coordinate,
            round_number=round_number,
            state_checksum=state_checksum,
            tensor_path=None,
        )
        rounds.append(
            FederatedRoundResult(
                round_number=round_number,
                client_results=tuple(client_results),
                aggregate_loss=aggregate_loss,
                communication=communication,
                global_state_reference=global_reference,
                personalized_state_references=(),
            )
        )

        if round_number in candidate_rounds:
            snapshots.append(create_round_snapshot(round_number, aggregated, aggregate_loss))

    history = FederatedTrainingHistory(coordinate=request.coordinate, rounds=tuple(rounds))
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple((client.client, client.preprocessing_checksum) for client in prepared_clients)
    )

    candidates = retain_checkpoint_candidates(
        request.coordinate,
        tuple(snapshots),
        checkpoint_protocol=request.checkpoint_protocol,
        autoencoder=request.autoencoder,
        output_directory=request.output_directory,
        preprocessing_state_set_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        client=None,
        device=device,
    )

    training_result = FederatedTrainingResult(
        coordinate=request.coordinate,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=preprocessing_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=torch.cuda.get_device_name(device),
        batch_size_used=request.batch_size,
    )
    return FederatedTrainingOutcome(training_result=training_result, candidates=candidates)


def _resolve_proximal_coefficient(
    protocol: FedAvgProtocol | FedProxProtocol,
) -> ProximalCoefficient | None:
    match protocol:
        case FedAvgProtocol():
            return None
        case FedProxProtocol(coefficient=coefficient):
            return coefficient
        case _:
            raise ScientificContractError(
                f"unsupported training protocol {type(protocol).__name__}",
                subject=ContractSubject.TRAINING,
            )
