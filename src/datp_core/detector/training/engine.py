from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path

import numpy as np
import polars as pl
import torch
from safetensors.torch import save
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.json import canonical_json_text
from datp_core.core.errors import (
    ErrorMessage,
    LeakageError,
    ScientificContractError,
)
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
    SeedDerivationComponent,
)
from datp_core.data.populations.contracts import (
    OUTCOME_LABEL_COLUMN,
    ClientIdentity,
    PopulationOutcomeLabel,
)
from datp_core.detector.autoencoder import (
    LEARNING_DTYPE,
    TORCH_LEARNING_DTYPE,
    AutoencoderModelState,
    ReconstructionAutoencoder,
    build_autoencoder_for_state,
    build_optimizer,
    build_reconstruction_autoencoder,
)
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.training.contracts import (
    AutoencoderProtocol,
    FedAvgProtocol,
    FedProxProtocol,
    OptimizerProtocol,
)
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
from datp_core.detector.training.protocols import (
    FEDERATED_DATALOADER_WORKER_COUNT,
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
                ErrorMessage("prepared features must be a two-dimensional tensor"),
                subject=ContractSubject.FEATURES,
            )
        if self.features_cpu.device.type != "cpu":
            raise ScientificContractError(
                ErrorMessage("prepared features must remain on CPU"),
                subject=ContractSubject.RUNTIME,
            )
        if self.features_cpu.dtype != TORCH_LEARNING_DTYPE:
            raise ScientificContractError(
                ErrorMessage("prepared features must use the canonical learning dtype"),
                subject=ContractSubject.FEATURES,
            )
        if self.features_cpu.shape[0] < 1:
            raise ScientificContractError(
                ErrorMessage("prepared client data requires at least one row"),
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
    progress_callback: Callable[[int, int], None] | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True, slots=True)
class ProximalTerm:
    reference_model_state: AutoencoderModelState
    coefficient: ProximalCoefficient | DittoRegularization


@dataclass(frozen=True, slots=True)
class LocalEpochResult:
    model_state: AutoencoderModelState
    mean_reconstruction_loss: MetricValue
    sample_count: RowCount


@dataclass(frozen=True, slots=True)
class SerializedStateEvidence:
    checksum: Checksum
    byte_count: ByteCount
    logical_element_count: LogicalElementCount


def reject_attack_rows_in_federated_training(labels: OutcomeLabelSequence) -> None:
    if any(label != PopulationOutcomeLabel.BENIGN.value for label in labels):
        raise LeakageError(
            ErrorMessage("attack-labelled rows cannot enter federated benign training"),
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
            ErrorMessage("federated training input is missing its declared label or feature schema"),
            subject=ContractSubject.SCHEMA,
        ) from exc

    reject_attack_rows_in_federated_training(labels)
    if len(labels) != matrix.shape[0]:
        raise ScientificContractError(
            ErrorMessage("federated labels and features must align by row"),
            subject=ContractSubject.ROWS,
        )
    if matrix.shape[1] != autoencoder.widths[0].value:
        raise ScientificContractError(
            ErrorMessage("feature width does not match the autoencoder input width"),
            subject=ContractSubject.FEATURES,
        )
    if not np.isfinite(matrix).all():
        raise ScientificContractError(
            ErrorMessage("federated training features must be finite"),
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


def _client_seed_component(
    client: ClientIdentity,
) -> SeedDerivationComponent:
    payload = canonical_json_text(
        {
            "population": client.population.value,
            "client_id": client.client_id.value,
            "identity_kind": client.identity_kind.value,
        }
    )
    digest = Checksum.from_text(payload).value
    return SeedDerivationComponent(int(digest[:16], 16) & 0x7FFF_FFFF)


def derive_client_stream_seed(
    training_seed: Seed,
    round_number: RoundNumber,
    client: ClientIdentity,
    stream: TrainingStream,
) -> Seed:
    round_seed = derive_worker_seed(training_seed, SeedDerivationComponent(round_number.value))
    client_seed = derive_worker_seed(round_seed, _client_seed_component(client))
    return derive_worker_seed(client_seed, SeedDerivationComponent(stream.value))


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
            ErrorMessage("proximal regularization requires model parameters"),
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
    reference = proximal_term.reference_model_state.to_torch_state_dict()
    try:
        return tuple(
            reference[name].detach().to(device=device, dtype=parameter.dtype)
            for name, parameter in model.named_parameters()
        )
    except KeyError as exc:
        raise ScientificContractError(
            ErrorMessage("proximal reference state does not match model parameters"),
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
) -> LocalEpochResult:
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
            ErrorMessage("local training produced no samples"),
            subject=ContractSubject.BATCH_SIZE,
        )
    return LocalEpochResult(
        model_state=AutoencoderModelState.from_model(model),
        mean_reconstruction_loss=MetricValue(float(weighted_reconstruction_loss.item()) / total_samples),
        sample_count=RowCount(total_samples),
    )


def train_client_update(
    *,
    client_data: PreparedFederatedClientData,
    initial_model_state: AutoencoderModelState,
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
        initial_model_state,
        device=device,
    )
    optimizer = build_optimizer(model, optimizer_protocol, learning_rate)
    loader = build_client_loader(
        client_data,
        batch_size=batch_size,
        seed=seed,
    )
    local_epoch = run_local_epoch(
        model,
        optimizer,
        loader,
        device,
        proximal_term=proximal_term,
    )
    return ClientUpdate(
        client=client_data.client,
        model_state=local_epoch.model_state,
        sample_count=local_epoch.sample_count,
        local_loss=local_epoch.mean_reconstruction_loss,
    )


def aggregate_client_updates(updates: Sequence[ClientUpdate]) -> AutoencoderModelState:
    return AutoencoderModelState.sample_weighted_average(updates)


def compute_weighted_aggregate_loss(updates: Sequence[ClientUpdate]) -> MetricValue:
    if not updates:
        raise ScientificContractError(
            ErrorMessage("aggregate loss requires at least one client update"),
            subject=ContractSubject.CLIENT,
        )
    total_samples = sum([update.sample_count.value for update in updates])
    if total_samples < 1:
        raise ScientificContractError(
            ErrorMessage("aggregate loss requires a positive total sample count"),
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
                "client_id": item.client.client_id.value,
                "identity_kind": item.client.identity_kind.value,
                "preprocessing_checksum": item.preprocessing_checksum.value,
            }
            for item in sorted(provenance, key=lambda value: value.client)
        ]
    )
    return Checksum.from_text(payload)


def serialize_and_checksum_model_state(
    model_state: AutoencoderModelState,
) -> SerializedStateEvidence:
    cpu_state = model_state.on_cpu_with_contiguous_tensors().to_torch_state_dict()
    payload = save(cpu_state)
    return SerializedStateEvidence(
        checksum=Checksum.from_bytes(payload),
        byte_count=ByteCount(len(payload)),
        logical_element_count=LogicalElementCount(len(cpu_state)),
    )


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
    model_state: AutoencoderModelState,
    loss: MetricValue,
) -> RoundSnapshot:
    return RoundSnapshot(
        round_number=round_number,
        model_state=model_state,
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
            ErrorMessage("federated training requires at least one client"),
            subject=ContractSubject.CLIENT,
        )
    identities = tuple(item.client for item in clients)
    identity_set = set(identities)

    if len(identity_set) != len(identities):
        raise ScientificContractError(
            ErrorMessage("federated training cannot receive duplicate clients"),
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if len(clients) != population_client_count.value:
        raise ScientificContractError(
            ErrorMessage("federated training client count does not match the declared population count"),
            subject=ContractSubject.CLIENT,
        )
    if training_seed != coordinate.training_seed:
        raise ScientificContractError(
            ErrorMessage("request and coordinate training seeds must match"),
            subject=ContractSubject.COORDINATE,
        )
    if any(client.population != coordinate.population for client in identity_set):
        raise ScientificContractError(
            ErrorMessage("every client must belong to the training coordinate population"),
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
                ErrorMessage(f"unsupported training protocol {type(protocol).__name__}"),
                subject=ContractSubject.TRAINING,
            )


def _run_training_round[T: FedAvgProtocol | FedProxProtocol](
    *,
    round_number: RoundNumber,
    request: FederatedTrainingRequest[T],
    prepared: tuple[PreparedFederatedClientData, ...],
    global_model_state: AutoencoderModelState,
    device: torch.device,
    proximal_coefficient: ProximalCoefficient | None,
) -> tuple[FederatedRoundResult, AutoencoderModelState]:
    updates: list[ClientUpdate] = []
    for client_data in prepared:
        seed = derive_client_stream_seed(
            request.training_seed,
            round_number,
            client_data.client,
            TrainingStream.GLOBAL_CLIENT_UPDATE,
        )
        proximal_term = (
            ProximalTerm(reference_model_state=global_model_state, coefficient=proximal_coefficient)
            if proximal_coefficient is not None
            else None
        )
        updates.append(
            train_client_update(
                client_data=client_data,
                initial_model_state=global_model_state,
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
    serialized_state = serialize_and_checksum_model_state(aggregated)

    communication = create_communication_record(
        round_number,
        serialized_state.byte_count,
        serialized_state.logical_element_count,
        upload_count=request.population_client_count,
        download_count=request.population_client_count,
    )

    round_result = FederatedRoundResult(
        round_number=round_number,
        client_results=tuple(ClientTrainingResult.from_update(update) for update in updates),
        aggregate_loss=aggregate_loss,
        communication=communication,
        global_state_reference=GlobalModelStateReference(
            coordinate=request.coordinate,
            round_number=round_number,
            state_checksum=serialized_state.checksum,
            tensor_path=None,
        ),
        personalized_state_references=(),
    )
    return round_result, aggregated


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
        PreparedClientProvenance(
            client=item.client,
            preprocessing_checksum=item.preprocessing_checksum,
        )
        for item in prepared
    )

    initial_model = build_reconstruction_autoencoder(
        request.autoencoder,
        initialization_seed=request.training_seed,
    )
    global_model_state = AutoencoderModelState.from_model(initial_model)

    candidate_rounds = frozenset(request.checkpoint_protocol.candidates)
    proximal_coefficient = _proximal_coefficient(request.training_protocol)
    rounds: list[FederatedRoundResult] = []
    snapshots: list[RoundSnapshot] = []

    for round_value in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_value)
        if request.progress_callback is not None:
            request.progress_callback(round_value, request.checkpoint_protocol.maximum_round.value)
        round_result, global_model_state = _run_training_round(
            round_number=round_number,
            request=request,
            prepared=prepared,
            global_model_state=global_model_state,
            device=device,
            proximal_coefficient=proximal_coefficient,
        )
        rounds.append(round_result)

        if round_number in candidate_rounds:
            snapshots.append(
                create_round_snapshot(
                    round_number,
                    global_model_state,
                    round_result.aggregate_loss,
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
