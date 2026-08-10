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
    LocalEpochCount,
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
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.training.contracts import (
    AutoencoderProtocol,
    FedAvgProtocol,
    FedProxProtocol,
    OptimizerProtocol,
)
from datp_core.detector.training.convergence import ConvergenceMonitor
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
    validation_features_cpu: torch.Tensor

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
        if self.validation_features_cpu.ndim != 2:
            raise ScientificContractError(
                ErrorMessage("prepared validation features must be a two-dimensional tensor"),
                subject=ContractSubject.FEATURES,
            )
        if self.validation_features_cpu.device.type != "cpu":
            raise ScientificContractError(
                ErrorMessage("prepared validation features must remain on CPU"),
                subject=ContractSubject.RUNTIME,
            )
        if self.validation_features_cpu.dtype != TORCH_LEARNING_DTYPE:
            raise ScientificContractError(
                ErrorMessage("prepared validation features must use the canonical learning dtype"),
                subject=ContractSubject.FEATURES,
            )
        if self.validation_features_cpu.shape[1] != self.features_cpu.shape[1]:
            raise ScientificContractError(
                ErrorMessage("prepared validation features must match the training feature width"),
                subject=ContractSubject.FEATURES,
            )
        if self.validation_features_cpu.shape[0] < 1:
            raise ScientificContractError(
                ErrorMessage("prepared client data requires at least one validation row"),
                subject=ContractSubject.ROWS,
            )


@dataclass(frozen=True, slots=True)
class FederatedTrainingRequest[T: FedAvgProtocol | FedProxProtocol]:
    coordinate: FederatedTrainingCoordinate
    clients: tuple[ClientTrainingInput, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: T
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    output_directory: Path
    progress_callback: Callable[[RoundNumber, RoundNumber], None] | None = field(
        default=None,
        compare=False,
        repr=False,
    )


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
    feature_names = client_input.feature_names.as_list()
    frame = client_input.training_features
    validation_frame = client_input.validation_features
    try:
        labels = OutcomeLabelSequence(
            tuple(OutcomeLabel(str(value)) for value in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
        )
        validation_labels = OutcomeLabelSequence(
            tuple(OutcomeLabel(str(value)) for value in validation_frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
        )
        matrix = frame.select(feature_names).to_numpy().astype(LEARNING_DTYPE, copy=False)
        validation_matrix = validation_frame.select(feature_names).to_numpy().astype(LEARNING_DTYPE, copy=False)
    except (pl.exceptions.ColumnNotFoundError, pl.exceptions.SchemaError) as exc:
        raise ScientificContractError(
            ErrorMessage("federated training input is missing its declared label or feature schema"),
            subject=ContractSubject.SCHEMA,
        ) from exc

    reject_attack_rows_in_federated_training(labels)
    reject_attack_rows_in_federated_training(validation_labels)
    if len(labels) != matrix.shape[0]:
        raise ScientificContractError(
            ErrorMessage("federated labels and features must align by row"),
            subject=ContractSubject.ROWS,
        )
    if len(validation_labels) != validation_matrix.shape[0]:
        raise ScientificContractError(
            ErrorMessage("federated validation labels and features must align by row"),
            subject=ContractSubject.ROWS,
        )
    if matrix.shape[1] != autoencoder.widths[0].value:
        raise ScientificContractError(
            ErrorMessage("feature width does not match the autoencoder input width"),
            subject=ContractSubject.FEATURES,
        )
    if validation_matrix.shape[1] != autoencoder.widths[0].value:
        raise ScientificContractError(
            ErrorMessage("validation feature width does not match the autoencoder input width"),
            subject=ContractSubject.FEATURES,
        )
    if not np.isfinite(matrix).all():
        raise ScientificContractError(
            ErrorMessage("federated training features must be finite"),
            subject=ContractSubject.FEATURES,
        )
    if not np.isfinite(validation_matrix).all():
        raise ScientificContractError(
            ErrorMessage("federated validation features must be finite"),
            subject=ContractSubject.FEATURES,
        )

    return PreparedFederatedClientData(
        client=client_input.client,
        features_cpu=torch.as_tensor(
            matrix,
            dtype=TORCH_LEARNING_DTYPE,
            device="cpu",
        ),
        validation_features_cpu=torch.as_tensor(
            validation_matrix,
            dtype=TORCH_LEARNING_DTYPE,
            device="cpu",
        ),
    )


def _client_seed_component(
    client: ClientIdentity,
) -> SeedDerivationComponent:
    payload = f"{client.population.value}|{client.client_id.value}|{client.identity_kind.value}"
    return SeedDerivationComponent(sum((index + 1) * ord(value) for index, value in enumerate(payload)) & 0x7FFF_FFFF)


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


def run_local_epoch_on_device(
    model: ReconstructionAutoencoder,
    optimizer: torch.optim.Optimizer,
    features: torch.Tensor,
    *,
    batch_size: BatchSize,
    seed: Seed,
    device: torch.device,
    proximal_term: ProximalTerm | None = None,
) -> LocalEpochResult:
    """Run one deterministic local epoch from a client tensor already on CUDA.

    Federated clients are trained sequentially because their updates must be
    aggregated in a stable order.  Keeping the active client's immutable input
    tensor on the selected device avoids a host-to-device transfer for every
    fixed-size batch; it does not change batching, shuffling, or optimization.
    """
    if features.device != device:
        raise ScientificContractError(
            ErrorMessage("device-local training features must be on the selected CUDA device"),
            subject=ContractSubject.RUNTIME,
        )
    generator = torch.Generator(device=device)
    generator.manual_seed(seed.value)
    order = torch.randperm(features.shape[0], generator=generator, device=device)
    reference_parameters = _reference_parameters(model, proximal_term, device)
    model.train()
    weighted_reconstruction_loss = torch.zeros((), device=device, dtype=TORCH_LEARNING_DTYPE)

    for start in range(0, features.shape[0], batch_size.value):
        batch_indices = order[start : start + batch_size.value]
        batch = features.index_select(0, batch_indices)
        loss = _train_one_batch(model, optimizer, batch, reference_parameters, proximal_term)
        weighted_reconstruction_loss = weighted_reconstruction_loss + loss * batch.shape[0]

    total_samples = features.shape[0]
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
    local_epochs: LocalEpochCount,
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
    features = client_data.features_cpu.to(device=device, dtype=TORCH_LEARNING_DTYPE, non_blocking=False)
    local_epoch = run_local_epoch_on_device(
        model,
        optimizer,
        features,
        batch_size=batch_size,
        seed=seed,
        device=device,
        proximal_term=proximal_term,
    )
    for epoch in range(1, local_epochs.value):
        epoch_seed = derive_worker_seed(seed, SeedDerivationComponent(epoch))
        local_epoch = run_local_epoch_on_device(
            model,
            optimizer,
            features,
            batch_size=batch_size,
            seed=epoch_seed,
            device=device,
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
    total_samples = sum(update.sample_count.value for update in updates)
    if total_samples < 1:
        raise ScientificContractError(
            ErrorMessage("aggregate loss requires a positive total sample count"),
            subject=ContractSubject.ROWS,
        )
    return MetricValue(sum(update.local_loss.value * update.sample_count.value for update in updates) / total_samples)


def compute_weighted_validation_loss(
    *,
    model_state: AutoencoderModelState,
    prepared: Sequence[PreparedFederatedClientData],
    autoencoder: AutoencoderProtocol,
    device: torch.device,
) -> MetricValue:

    if not prepared:
        raise ScientificContractError(
            ErrorMessage("validation loss requires at least one client"),
            subject=ContractSubject.CLIENT,
        )
    model = build_autoencoder_for_state(autoencoder, model_state, device=device)
    model.eval()
    weighted_loss = 0.0
    total_rows = 0
    with torch.no_grad():
        for client_data in prepared:
            validation_rows = client_data.validation_features_cpu.shape[0]
            if validation_rows < 1:
                raise ScientificContractError(
                    ErrorMessage("validation loss requires positive client validation rows"),
                    subject=ContractSubject.ROWS,
                )
            features = client_data.validation_features_cpu.to(
                device=device,
                dtype=TORCH_LEARNING_DTYPE,
                non_blocking=False,
            )
            reconstruction = model(features)
            loss = nn.functional.mse_loss(reconstruction, features)
            weighted_loss += float(loss.item()) * validation_rows
            total_rows += validation_rows
    return MetricValue(weighted_loss / total_rows)


def serialize_model_state(
    model_state: AutoencoderModelState,
) -> SerializedStateEvidence:
    cpu_state = model_state.on_cpu_with_contiguous_tensors().to_torch_state_dict()
    payload = save(cpu_state)
    return SerializedStateEvidence(
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
    convergence_enabled: bool,
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
                local_epochs=request.training_protocol.local_epochs,
                seed=seed,
                device=device,
                proximal_term=proximal_term,
            )
        )

    aggregated = aggregate_client_updates(updates)
    aggregate_loss = compute_weighted_aggregate_loss(updates)
    aggregate_validation_loss = (
        compute_weighted_validation_loss(
            model_state=aggregated,
            prepared=prepared,
            autoencoder=request.autoencoder,
            device=device,
        )
        if convergence_enabled
        else None
    )
    serialized_state = serialize_model_state(aggregated)

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
            tensor_path=None,
        ),
        personalized_state_references=(),
        aggregate_validation_loss=aggregate_validation_loss,
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

    initial_model = build_reconstruction_autoencoder(
        request.autoencoder,
        initialization_seed=request.training_seed,
    )
    global_model_state = AutoencoderModelState.from_model(initial_model)

    convergence = request.diagnostic_snapshot_protocol.convergence
    monitor = ConvergenceMonitor(request.diagnostic_snapshot_protocol) if convergence is not None else None
    proximal_coefficient = _proximal_coefficient(request.training_protocol)
    rounds: list[FederatedRoundResult] = []

    for round_value in range(1, request.diagnostic_snapshot_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_value)
        if request.progress_callback is not None:
            request.progress_callback(round_number, request.diagnostic_snapshot_protocol.maximum_round)
        round_result, global_model_state = _run_training_round(
            round_number=round_number,
            request=request,
            prepared=prepared,
            global_model_state=global_model_state,
            device=device,
            proximal_coefficient=proximal_coefficient,
            convergence_enabled=monitor is not None,
        )
        rounds.append(round_result)

        if monitor is not None:
            validation_loss = round_result.aggregate_validation_loss
            if validation_loss is None:
                raise ScientificContractError(
                    ErrorMessage("convergence requires an aggregate benign validation loss"),
                    subject=ContractSubject.TRAINING,
                )
            monitor.record(validation_loss)
            if monitor.should_stop(round_number):
                break

    history = FederatedTrainingHistory(
        coordinate=request.coordinate,
        rounds=tuple(rounds),
    )
    result = FederatedTrainingResult(
        coordinate=request.coordinate,
        autoencoder=request.autoencoder,
        diagnostic_snapshot_protocol=request.diagnostic_snapshot_protocol,
        history=history,
        terminal_model_state=global_model_state.on_cpu_with_contiguous_tensors(),
        device_name=CudaDeviceName(torch.cuda.get_device_name(device).strip()),
        batch_size_used=request.batch_size,
    )

    return FederatedTrainingExecution(training_result=result)
