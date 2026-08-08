from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import numpy as np
import polars as pl
import torch
from safetensors.torch import save
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.artifacts.provenance import Checksum, checksum_bytes, checksum_text
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import LeakageError, ScientificContractError
from datp_core.core.identifiers import (
    CommunicationEstimationMethod,
    ContractSubject,
    CudaDeviceName,
    OutcomeLabel,
    OutcomeLabelSequence,
)
from datp_core.core.numeric import (
    BatchSize,
    ByteCount,
    ClientCount,
    DittoRegularization,
    LearningRate,
    LogicalElementCount,
    MetricValue,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    Seed,
)
from datp_core.data.populations.contracts import (
    OUTCOME_LABEL_COLUMN,
    ClientIdentity,
    PopulationOutcomeLabel,
)
from datp_core.detector.autoencoder import (
    LEARNING_DTYPE,
    TORCH_LEARNING_DTYPE,
    AutoencoderState,
    AutoencoderStateView,
    ReconstructionAutoencoder,
    build_autoencoder_for_state,
    build_optimizer,
    build_reconstruction_autoencoder,
    clone_autoencoder_state,
    clone_state,
)
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.models import (
    ClientTrainingInput,
    ClientTrainingResult,
    ClientUpdate,
    CommunicationRecord,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingExecution,
    FederatedTrainingHistory,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PreparedClientProvenance,
    RoundSnapshot,
)
from datp_core.protocols.training import (
    FEDERATED_DATALOADER_WORKER_COUNT,
    FedAvgProtocol,
    FedProxProtocol,
    OptimizerProtocol,
)
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.runtime.determinism import configure_deterministic_execution, derive_worker_seed


class TrainingStream(IntEnum):
    GLOBAL_CLIENT_UPDATE = 1
    PERSONALIZED_CLIENT_UPDATE = 2


@dataclass(frozen=True, slots=True, eq=False)
class PreparedFederatedClientData:
    client: ClientIdentity
    features_cpu: torch.Tensor
    preprocessing_checksum: Checksum

    def __post_init__(self) -> None:
        if self.features_cpu.ndim != 2:
            raise ScientificContractError(
                "prepared features must be a two-dimensional tensor",
                subject=ContractSubject.FEATURES,
            )
        if self.features_cpu.device.type != "cpu":
            raise ScientificContractError(
                "prepared features must remain on CPU",
                subject=ContractSubject.RUNTIME,
            )
        if self.features_cpu.dtype != TORCH_LEARNING_DTYPE:
            raise ScientificContractError(
                "prepared features must use the canonical learning dtype",
                subject=ContractSubject.FEATURES,
            )
        if self.features_cpu.shape[0] < 1:
            raise ScientificContractError(
                "prepared client data requires at least one row",
                subject=ContractSubject.ROWS,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingRequest[T: FedAvgProtocol | FedProxProtocol]:
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


@dataclass(frozen=True, slots=True)
class ProximalTerm:
    reference_state: AutoencoderStateView
    coefficient: ProximalCoefficient | DittoRegularization


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
    frame = client_input.training_features
    try:
        labels = OutcomeLabelSequence(
            tuple(OutcomeLabel(str(value)) for value in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
        )
        matrix = frame.select(client_input.feature_names.as_list()).to_numpy().astype(LEARNING_DTYPE, copy=False)
    except (pl.exceptions.ColumnNotFoundError, pl.exceptions.SchemaError) as exc:
        raise ScientificContractError(
            "federated training input is missing its declared label or feature schema",
            subject=ContractSubject.SCHEMA,
        ) from exc

    reject_attack_rows_in_federated_training(labels)
    if len(labels) != matrix.shape[0]:
        raise ScientificContractError(
            "federated labels and features must align by row",
            subject=ContractSubject.ROWS,
        )
    if matrix.shape[1] != autoencoder.widths[0].value:
        raise ScientificContractError(
            "feature width does not match the autoencoder input width",
            subject=ContractSubject.FEATURES,
        )
    if not np.isfinite(matrix).all():
        raise ScientificContractError(
            "federated training features must be finite",
            subject=ContractSubject.FEATURES,
        )

    return PreparedFederatedClientData(
        client=client_input.client,
        features_cpu=torch.as_tensor(
            matrix,
            dtype=TORCH_LEARNING_DTYPE,
            device="cpu",
        ),
        preprocessing_checksum=client_input.preprocessing_state.estimator_checksum,
    )


def _client_seed_component(client: ClientIdentity) -> int:
    payload = canonical_json_text(
        {
            "population": client.population.value,
            "client_id": client.client_id,
            "identity_kind": client.identity_kind.value,
        }
    )
    digest = checksum_text(payload).value
    return int(digest[:16], 16) & 0x7FFF_FFFF


def derive_client_stream_seed(
    training_seed: Seed,
    round_number: RoundNumber,
    client: ClientIdentity,
    stream: TrainingStream,
) -> Seed:
    round_seed = derive_worker_seed(training_seed, round_number.value)
    client_seed = derive_worker_seed(round_seed, _client_seed_component(client))
    return derive_worker_seed(client_seed, stream.value)


def build_client_loader(
    data: PreparedFederatedClientData,
    *,
    batch_size: BatchSize,
    seed: Seed,
) -> DataLoader[tuple[torch.Tensor, ...]]:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed.value)
    return DataLoader(
        TensorDataset(data.features_cpu),
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
    if not local_parameters:
        raise ScientificContractError(
            "proximal regularization requires model parameters",
            subject=ContractSubject.TRAINING,
        )
    squared_diffs = [
        torch.sum(torch.square(local - reference))
        for local, reference in zip(local_parameters, reference_parameters, strict=True)
    ]
    return torch.stack(squared_diffs).sum() * (coefficient.value / 2.0)


def _reference_parameters(
    model: ReconstructionAutoencoder,
    proximal_term: ProximalTerm | None,
    device: torch.device,
) -> tuple[torch.Tensor, ...] | None:
    if proximal_term is None:
        return None
    reference = proximal_term.reference_state
    try:
        return tuple(
            [
                reference[name].detach().to(device=device, dtype=parameter.dtype)
                for name, parameter in model.named_parameters()
            ]
        )
    except KeyError as exc:
        raise ScientificContractError(
            "proximal reference state does not match model parameters",
            subject=ContractSubject.TRAINING,
        ) from exc


def _train_one_batch(
    model: ReconstructionAutoencoder,
    optimizer: torch.optim.Optimizer,
    batch: torch.Tensor,
    reference_parameters: tuple[torch.Tensor, ...] | None,
    proximal_term: ProximalTerm | None,
) -> torch.Tensor:
    optimizer.zero_grad(set_to_none=True)
    reconstruction = model(batch)
    reconstruction_loss = nn.functional.mse_loss(reconstruction, batch)
    objective = reconstruction_loss

    if reference_parameters is not None and proximal_term is not None:
        local_parameters = tuple(parameter for _, parameter in model.named_parameters())
        objective = objective + proximal_penalty(
            local_parameters,
            reference_parameters,
            proximal_term.coefficient,
        )

    torch.autograd.backward(objective)
    optimizer.step()
    return reconstruction_loss.detach()


def run_local_epoch(
    model: ReconstructionAutoencoder,
    optimizer: torch.optim.Optimizer,
    loader: DataLoader[tuple[torch.Tensor, ...]],
    device: torch.device,
    *,
    proximal_term: ProximalTerm | None = None,
) -> tuple[AutoencoderState, MetricValue, RowCount]:
    reference_parameters = _reference_parameters(model, proximal_term, device)
    model.train()
    weighted_reconstruction_loss = torch.zeros((), device=device, dtype=TORCH_LEARNING_DTYPE)
    total_samples = 0

    for (batch_cpu,) in loader:
        batch_size = batch_cpu.shape[0]
        batch = batch_cpu.to(
            device=device,
            dtype=TORCH_LEARNING_DTYPE,
            non_blocking=False,
        )
        batch_loss = _train_one_batch(
            model,
            optimizer,
            batch,
            reference_parameters,
            proximal_term,
        )
        weighted_reconstruction_loss = weighted_reconstruction_loss + batch_loss * batch_size
        total_samples += batch_size

    if total_samples < 1:
        raise ScientificContractError(
            "local training produced no samples",
            subject=ContractSubject.BATCH_SIZE,
        )
    return (
        clone_state(model.state_dict()),
        MetricValue(float(weighted_reconstruction_loss.item()) / total_samples),
        RowCount(total_samples),
    )


def train_client_update(
    *,
    client_data: PreparedFederatedClientData,
    initial_state: AutoencoderStateView,
    autoencoder: AutoencoderProtocol,
    optimizer_protocol: OptimizerProtocol,
    learning_rate: LearningRate,
    batch_size: BatchSize,
    seed: Seed,
    device: torch.device,
    proximal_term: ProximalTerm | None = None,
) -> ClientUpdate:
    model = build_autoencoder_for_state(
        autoencoder,
        initial_state,
        device=device,
    )
    optimizer = build_optimizer(model, optimizer_protocol, learning_rate)
    loader = build_client_loader(
        client_data,
        batch_size=batch_size,
        seed=seed,
    )
    state, loss, sample_count = run_local_epoch(
        model,
        optimizer,
        loader,
        device,
        proximal_term=proximal_term,
    )
    return ClientUpdate(
        client=client_data.client,
        state_dict=state,
        sample_count=sample_count,
        local_loss=loss,
    )


def aggregate_client_updates(updates: Sequence[ClientUpdate]) -> AutoencoderState:
    if not updates:
        raise ScientificContractError(
            "aggregation requires at least one client update",
            subject=ContractSubject.CLIENT,
        )
    total_samples = sum([update.sample_count.value for update in updates])
    if total_samples < 1:
        raise ScientificContractError(
            "aggregation requires a positive total sample count",
            subject=ContractSubject.ROWS,
        )

    reference_state = updates[0].state_dict
    reference_keys = tuple(reference_state.keys())

    for update in updates[1:]:
        if tuple(update.state_dict.keys()) != reference_keys:
            raise ScientificContractError(
                "client update parameter keys do not match",
                subject=ContractSubject.TRAINING,
            )
        for name in reference_keys:
            expected = reference_state[name]
            observed = update.state_dict[name]
            if expected.shape != observed.shape or expected.dtype != observed.dtype:
                raise ScientificContractError(
                    "client update parameter shapes or dtypes do not match",
                    subject=ContractSubject.TRAINING,
                )

    weights = [update.sample_count.value / total_samples for update in updates]
    aggregated: AutoencoderState = {}

    for name in reference_keys:
        weighted_sum = torch.zeros_like(reference_state[name], dtype=torch.float64)
        for update, weight in zip(updates, weights, strict=True):
            weighted_sum.add_(update.state_dict[name].to(torch.float64), alpha=weight)
        aggregated[name] = weighted_sum.to(reference_state[name].dtype)

    return aggregated


def compute_weighted_aggregate_loss(updates: Sequence[ClientUpdate]) -> MetricValue:
    if not updates:
        raise ScientificContractError(
            "aggregate loss requires at least one client update",
            subject=ContractSubject.CLIENT,
        )
    total_samples = sum([update.sample_count.value for update in updates])
    if total_samples < 1:
        raise ScientificContractError(
            "aggregate loss requires a positive total sample count",
            subject=ContractSubject.ROWS,
        )
    return MetricValue(sum([update.local_loss.value * update.sample_count.value for update in updates]) / total_samples)


def preprocessing_state_set_checksum(
    provenance: Sequence[PreparedClientProvenance],
) -> Checksum:
    payload = canonical_json_text(
        [
            {
                "population": item.client.population.value,
                "client_id": item.client.client_id,
                "identity_kind": item.client.identity_kind.value,
                "preprocessing_checksum": item.preprocessing_checksum.value,
            }
            for item in sorted(provenance, key=lambda value: value.client)
        ]
    )
    return checksum_text(payload)


def serialize_and_checksum_state_dict(
    state_dict: AutoencoderStateView,
) -> tuple[Checksum, ByteCount, LogicalElementCount]:
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    payload = save(cpu_state)
    return checksum_bytes(payload), ByteCount(len(payload)), LogicalElementCount(len(cpu_state))


def create_communication_record(
    round_number: RoundNumber,
    state_bytes: ByteCount,
    logical_element_count: LogicalElementCount,
    *,
    upload_count: ClientCount,
    download_count: ClientCount,
) -> CommunicationRecord:
    return CommunicationRecord(
        round_number=round_number,
        estimated_upload_bytes=ByteCount(upload_count.value * state_bytes.value),
        estimated_download_bytes=ByteCount(download_count.value * state_bytes.value),
        estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
        state_bytes=state_bytes,
        logical_element_count=logical_element_count,
    )


def create_round_snapshot(
    round_number: RoundNumber,
    state: AutoencoderStateView,
    loss: MetricValue,
) -> RoundSnapshot:
    return RoundSnapshot(
        round_number=round_number,
        state_dict=clone_state(state),
        mean_training_loss=loss,
    )


def validate_common_request(
    coordinate: FederatedTrainingCoordinate,
    training_seed: Seed,
    clients: tuple[ClientTrainingInput, ...],
    population_client_count: ClientCount,
) -> None:
    if not clients:
        raise ScientificContractError(
            "federated training requires at least one client",
            subject=ContractSubject.CLIENT,
        )
    identities = tuple(item.client for item in clients)
    identity_set = set(identities)

    if len(identity_set) != len(identities):
        raise ScientificContractError(
            "federated training cannot receive duplicate clients",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if len(clients) != population_client_count.value:
        raise ScientificContractError(
            "federated training client count does not match the declared population count",
            subject=ContractSubject.CLIENT,
        )
    if training_seed != coordinate.training_seed:
        raise ScientificContractError(
            "request and coordinate training seeds must match",
            subject=ContractSubject.COORDINATE,
        )
    if any(client.population != coordinate.population for client in identity_set):
        raise ScientificContractError(
            "every client must belong to the training coordinate population",
            subject=ContractSubject.CLIENT_IDENTITY,
        )


def _proximal_coefficient(
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


def run_federated_training[T: FedAvgProtocol | FedProxProtocol](
    request: FederatedTrainingRequest[T],
) -> FederatedTrainingExecution:
    validate_common_request(
        request.coordinate,
        request.training_seed,
        request.clients,
        request.population_client_count,
    )
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()

    ordered_inputs = tuple(sorted(request.clients, key=lambda item: item.client))
    prepared = tuple(prepare_federated_client_data(item, request.autoencoder) for item in ordered_inputs)

    provenance = tuple(
        [
            PreparedClientProvenance(
                client=item.client,
                preprocessing_checksum=item.preprocessing_checksum,
            )
            for item in prepared
        ]
    )

    initial_model = build_reconstruction_autoencoder(
        request.autoencoder,
        initialization_seed=request.training_seed,
    )
    global_state = clone_autoencoder_state(initial_model)

    candidate_rounds = frozenset(request.checkpoint_protocol.candidates)
    proximal_coefficient = _proximal_coefficient(request.training_protocol)
    rounds: list[FederatedRoundResult] = []
    snapshots: list[RoundSnapshot] = []

    for round_value in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_value)
        updates: list[ClientUpdate] = []

        for client_data in prepared:
            seed = derive_client_stream_seed(
                request.training_seed,
                round_number,
                client_data.client,
                TrainingStream.GLOBAL_CLIENT_UPDATE,
            )
            proximal_term = (
                ProximalTerm(global_state, proximal_coefficient) if proximal_coefficient is not None else None
            )
            updates.append(
                train_client_update(
                    client_data=client_data,
                    initial_state=global_state,
                    autoencoder=request.autoencoder,
                    optimizer_protocol=request.training_protocol.optimizer,
                    learning_rate=request.learning_rate,
                    batch_size=request.batch_size,
                    seed=seed,
                    device=device,
                    proximal_term=proximal_term,
                )
            )

        aggregated = aggregate_client_updates(updates)
        aggregate_loss = compute_weighted_aggregate_loss(updates)
        state_checksum, state_size, logical_elements = serialize_and_checksum_state_dict(aggregated)

        communication = create_communication_record(
            round_number,
            state_size,
            logical_elements,
            upload_count=request.population_client_count,
            download_count=request.population_client_count,
        )

        rounds.append(
            FederatedRoundResult(
                round_number=round_number,
                client_results=tuple(ClientTrainingResult.from_update(update) for update in updates),
                aggregate_loss=aggregate_loss,
                communication=communication,
                global_state_reference=GlobalModelStateReference(
                    coordinate=request.coordinate,
                    round_number=round_number,
                    state_checksum=state_checksum,
                    tensor_path=None,
                ),
                personalized_state_references=(),
            )
        )
        global_state = aggregated

        if round_number in candidate_rounds:
            snapshots.append(
                create_round_snapshot(
                    round_number,
                    global_state,
                    aggregate_loss,
                )
            )

    history = FederatedTrainingHistory(
        coordinate=request.coordinate,
        rounds=tuple(rounds),
    )
    result = FederatedTrainingResult(
        coordinate=request.coordinate,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        history=history,
        preprocessing_state_set_checksum=preprocessing_state_set_checksum(provenance),
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=CudaDeviceName(torch.cuda.get_device_name(device).strip()),
        batch_size_used=request.batch_size,
    )

    return FederatedTrainingExecution(
        training_result=result,
        snapshots=tuple(snapshots),
    )
