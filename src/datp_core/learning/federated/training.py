"""Shared client-local training mechanics reused by FedAvg, FedProx, and Ditto."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import numpy as np
import polars as pl
import torch
from safetensors.torch import save
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.domain.enums import (
    CommunicationEstimationMethod,
    ContractSubject,
    OptimizerId,
    PopulationIdentityKind,
    ProcessedDataBranch,
)
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
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
    ModelStateMap,
    ReconstructionAutoencoder,
    build_reconstruction_autoencoder,
    clone_autoencoder_state,
    load_autoencoder_state,
)
from datp_core.learning.federated.models import (
    ClientTrainingInput,
    ClientTrainingResult,
    ClientUpdate,
    CommunicationRecord,
    FederatedHistoryAssetName,
    FederatedHistoryColumn,
    FederatedRoundResult,
    FederatedTrainingCoordinate,
    FederatedTrainingHistory,
    FederatedTrainingOutcome,
    FederatedTrainingResult,
    GlobalModelStateReference,
    PersonalizedModelStateReference,
    RoundSnapshot,
)
from datp_core.populations.models import (
    OUTCOME_LABEL_COLUMN,
    ClientIdentity,
    PopulationOutcomeLabel,
)
from datp_core.preprocessing.models import FittedPreprocessingState
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

ROUND_SUMMARY_SCHEMA: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.AGGREGATE_LOSS.value: pl.Float64,
    FederatedHistoryColumn.UPLOAD_BYTES.value: pl.Int64,
    FederatedHistoryColumn.DOWNLOAD_BYTES.value: pl.Int64,
    FederatedHistoryColumn.GLOBAL_STATE_CHECKSUM.value: pl.String,
}

CLIENT_ROUNDS_SCHEMA: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.CLIENT_ID.value: pl.String,
    FederatedHistoryColumn.SAMPLE_COUNT.value: pl.Int64,
    FederatedHistoryColumn.LOCAL_LOSS.value: pl.Float64,
}

PERSONALIZED_ROUNDS_SCHEMA: Mapping[str, type[pl.DataType]] = {
    FederatedHistoryColumn.ROUND_NUMBER.value: pl.Int64,
    FederatedHistoryColumn.CLIENT_ID.value: pl.String,
    FederatedHistoryColumn.LOCAL_LOSS.value: pl.Float64,
    FederatedHistoryColumn.STATE_CHECKSUM.value: pl.String,
}


def _validate_schema(frame: pl.DataFrame, expected_schema: Mapping[str, type[pl.DataType]]) -> None:
    expected_cols = list(expected_schema.keys())
    if set(frame.columns) != set(expected_cols) or list(frame.columns) != expected_cols:
        raise ArtifactIntegrityError(
            "Parquet table columns do not match expected schema exactly in names and order",
            subject=ContractSubject.SCHEMA,
        )
    for col, dtype in expected_schema.items():
        if frame.schema[col] != dtype:
            raise ArtifactIntegrityError(
                f"Parquet column '{col}' has type {frame.schema[col]}, expected {dtype}",
                subject=ContractSubject.SCHEMA,
            )





@dataclass(frozen=True, slots=True)
class PreparedFederatedClientData:
    client: ClientIdentity
    features_cpu: torch.Tensor
    preprocessing_checksum: Checksum


@dataclass(frozen=True, slots=True)
class FederatedTrainingRequest:
    coordinate: FederatedTrainingCoordinate
    clients: tuple[ClientTrainingInput, ...]
    population_client_count: ClientCount
    autoencoder: AutoencoderProtocol
    training_protocol: FedAvgProtocol | FedProxProtocol
    checkpoint_protocol: CheckpointProtocol
    training_seed: Seed
    batch_size: BatchSize
    learning_rate: LearningRate
    split_manifest_checksum: Checksum
    output_directory: Path


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
    """Validate client data once before round loop and store complete CPU tensors."""
    reject_centralized_preprocessing_for_federated_training(client_input.preprocessing_state)
    if client_input.preprocessing_state.client_identity is None or client_input.preprocessing_state.client_identity.value != client_input.client.client_id:
        raise ScientificContractError(
            "preprocessing client identity does not match input client",
            subject=ContractSubject.CLIENT_IDENTITY,
        )

    labels = OutcomeLabelSequence(tuple(str(value) for value in client_input.training_features.get_column(OUTCOME_LABEL_COLUMN).to_list()))
    reject_attack_rows_in_federated_training(labels)

    matrix = client_input.training_features.select(client_input.feature_names.as_list()).to_numpy().astype(LEARNING_DTYPE, copy=False)
    if not np.isfinite(matrix).all():
        raise ScientificContractError("federated features must be finite", subject=ContractSubject.FEATURES)
    if matrix.shape[0] < 1:
        raise ScientificContractError("client training input requires at least one row", subject=ContractSubject.ROWS)
    if matrix.shape[1] != autoencoder.widths[0]:
        raise ScientificContractError("feature width mismatch during dataset preparation", subject=ContractSubject.FEATURES)
    if len(labels) != matrix.shape[0]:
        raise ScientificContractError("federated arrays must align by row", subject=ContractSubject.ROWS)

    features_cpu = torch.tensor(matrix, dtype=torch.float32, device="cpu")
    return PreparedFederatedClientData(
        client=client_input.client,
        features_cpu=features_cpu,
        preprocessing_checksum=client_input.preprocessing_state.estimator_checksum,
    )


def client_round_seed(
    training_seed: Seed,
    round_number: RoundNumber,
    client_index: int,
) -> Seed:
    """Deterministic per-round per-client seed derived from training seed."""
    round_seed = derive_worker_seed(training_seed, round_number.value)
    return derive_worker_seed(round_seed, client_index)


def build_client_loader(
    data: PreparedFederatedClientData,
    *,
    batch_size: BatchSize,
    seed: Seed,
) -> DataLoader:
    """Build a CPU DataLoader for federated client training batches."""
    features_cpu = data.features_cpu
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


def preprocessing_state_set_checksum(
    client_checksum_pairs: Sequence[tuple[ClientIdentity, Checksum]],
) -> Checksum:
    """One deterministic checksum binding every client identity to its preprocessing checksum."""
    entries = sorted(f"{client.client_id}:{checksum.value}" for client, checksum in client_checksum_pairs)
    return Checksum(sha256("|".join(entries).encode()).hexdigest())


def serialized_state_dict_bytes(state_dict: ModelStateMap) -> bytes:
    cpu_state = {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}
    return save(cpu_state)


def checksum_state_dict(state_dict: ModelStateMap) -> Checksum:
    return Checksum(sha256(serialized_state_dict_bytes(state_dict)).hexdigest())


def serialize_and_checksum_state_dict(
    state_dict: ModelStateMap,
) -> tuple[bytes, Checksum, ByteCount]:
    """Serialize state dict once and return serialized bytes, checksum, and byte count."""
    payload = serialized_state_dict_bytes(state_dict)
    checksum = Checksum(sha256(payload).hexdigest())
    byte_count = ByteCount(len(payload))
    return payload, checksum, byte_count


def validate_federated_training_request(request: FederatedTrainingRequest) -> None:
    if not request.clients:
        raise ScientificContractError(
            "training requires at least one client dataset",
            subject=ContractSubject.CLIENT,
        )
    client_ids = tuple(item.client.client_id for item in request.clients)
    if len(set(client_ids)) != len(client_ids):
        raise ScientificContractError(
            "training cannot receive duplicate client identities",
            subject=ContractSubject.CLIENT_IDENTITY,
        )
    if len(request.clients) != request.population_client_count.value:
        raise ScientificContractError(
            "training requires exactly the declared population client count",
            subject=ContractSubject.CLIENT,
        )
    if request.batch_size.value < 1:
        raise ScientificContractError(
            "training batch size must remain positive",
            subject=ContractSubject.BATCH_SIZE,
        )
    for client_input in request.clients:
        reject_centralized_preprocessing_for_federated_training(client_input.preprocessing_state)
        if client_input.preprocessing_state.client_identity is None or client_input.preprocessing_state.client_identity.value != client_input.client.client_id:
            raise ScientificContractError(
                "preprocessing state client identity must match client training input",
                subject=ContractSubject.CLIENT_IDENTITY,
            )


def run_federated_training(
    request: FederatedTrainingRequest,
    *,
    proximal_coefficient: ProximalCoefficient | None,
) -> FederatedTrainingOutcome:
    validate_federated_training_request(request)
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()

    ordered_clients = tuple(sorted(request.clients, key=lambda item: item.client))
    prepared_clients: list[PreparedFederatedClientData] = [
        prepare_federated_client_data(client_input, request.autoencoder)
        for client_input in ordered_clients
    ]

    global_model = build_reconstruction_autoencoder(request.autoencoder, initialization_seed=request.training_seed)
    global_model.to(device)
    global_state = clone_autoencoder_state(global_model)
    del global_model

    candidate_rounds = {candidate.value for candidate in request.checkpoint_protocol.candidates}
    rounds: list[FederatedRoundResult] = []
    snapshots: list[RoundSnapshot] = []

    for round_index in range(1, request.checkpoint_protocol.maximum_round.value + 1):
        round_number = RoundNumber(round_index)
        client_updates: list[ClientUpdate] = []
        client_results: list[ClientTrainingResult] = []
        reference_state = {name: tensor.to(device) for name, tensor in global_state.items()}

        for client_index, client_data in enumerate(prepared_clients):
            client_seed = client_round_seed(request.training_seed, round_number, client_index)
            local_model = ReconstructionAutoencoder(request.autoencoder.widths).to(device)
            load_autoencoder_state(local_model, {name: tensor.clone() for name, tensor in reference_state.items()})
            optimizer = build_optimizer(local_model, request.training_protocol.optimizer, request.learning_rate)
            loader = build_client_loader(client_data, batch_size=request.batch_size, seed=client_seed)
            proximal_term = (
                ProximalTerm(reference_state=reference_state, coefficient=proximal_coefficient)
                if proximal_coefficient is not None
                else None
            )
            local_state, local_loss, sample_count = run_local_epoch(
                local_model, optimizer, loader, device, proximal_term=proximal_term
            )
            client = client_data.client
            client_updates.append(
                ClientUpdate(client=client, state_dict=local_state, sample_count=sample_count, local_loss=local_loss)
            )
            client_results.append(ClientTrainingResult(client=client, sample_count=sample_count, local_loss=local_loss))

        aggregated = aggregate_client_updates(client_updates)
        global_state = aggregated

        total_samples = sum(u.sample_count.value for u in client_updates)
        aggregate_loss = MetricValue(
            sum(u.local_loss.value * u.sample_count.value for u in client_updates) / total_samples
        )
        _, state_checksum, single_state_bytes = serialize_and_checksum_state_dict(aggregated)
        upload_bytes = len(client_updates) * single_state_bytes.value
        download_bytes = len(ordered_clients) * single_state_bytes.value

        communication = CommunicationRecord(
            round_number=round_number,
            estimated_upload_bytes=ByteCount(upload_bytes),
            estimated_download_bytes=ByteCount(download_bytes),
            estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
        )
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

        if round_index in candidate_rounds:
            snapshots.append(
                RoundSnapshot(
                    round_number,
                    {name: tensor.clone() for name, tensor in aggregated.items()},
                    aggregate_loss,
                )
            )

    history = FederatedTrainingHistory(coordinate=request.coordinate, rounds=tuple(rounds))
    preprocessing_checksum = preprocessing_state_set_checksum(
        tuple((client.client, client.preprocessing_checksum) for client in prepared_clients)
    )

    from datp_core.learning.federated.checkpointing import retain_checkpoint_candidates

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


def persist_federated_training_history(
    history: FederatedTrainingHistory,
    directory: Path,
    *,
    device_name: str,
) -> None:
    if not device_name:
        raise ArtifactIntegrityError(
            "training publication requires a non-empty device name",
            subject=ContractSubject.CUDA,
        )
    directory.mkdir(parents=True, exist_ok=True)
    (directory / FederatedHistoryAssetName.DEVICE_NAME.value).write_text(device_name, encoding="utf-8")

    col = FederatedHistoryColumn
    round_rows = [
        (
            r.round_number.value,
            r.aggregate_loss.value,
            r.communication.estimated_upload_bytes.value,
            r.communication.estimated_download_bytes.value,
            r.global_state_reference.state_checksum.value,
        )
        for r in history.rounds
    ]
    client_rows = [
        (
            r.round_number.value,
            cr.client.client_id,
            cr.sample_count.value,
            cr.local_loss.value,
        )
        for r in history.rounds
        for cr in r.client_results
    ]
    personalized_rows = [
        (
            r.round_number.value,
            pr.client.client_id,
            pr.local_loss.value,
            pr.state_checksum.value,
        )
        for r in history.rounds
        for pr in r.personalized_state_references
    ]

    pl.DataFrame(round_rows, schema=ROUND_SUMMARY_SCHEMA, orient="row").write_parquet(
        directory / FederatedHistoryAssetName.ROUND_SUMMARY.value
    )
    pl.DataFrame(client_rows, schema=CLIENT_ROUNDS_SCHEMA, orient="row").write_parquet(
        directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value
    )
    if personalized_rows:
        pl.DataFrame(personalized_rows, schema=PERSONALIZED_ROUNDS_SCHEMA, orient="row").write_parquet(
            directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value
        )


def load_federated_training_history(
    coordinate: FederatedTrainingCoordinate,
    directory: Path,
    identity_kind: PopulationIdentityKind,
    *,
    personalized_coordinate: FederatedTrainingCoordinate | None = None,
) -> FederatedTrainingHistory:
    col = FederatedHistoryColumn
    round_summary_path = directory / FederatedHistoryAssetName.ROUND_SUMMARY.value
    client_rounds_path = directory / FederatedHistoryAssetName.CLIENT_ROUNDS.value
    if not round_summary_path.is_file() or not client_rounds_path.is_file():
        raise ArtifactIntegrityError("history parquet file missing", subject=ContractSubject.ARTIFACT_PATH)

    round_frame = pl.read_parquet(round_summary_path).sort(col.ROUND_NUMBER.value)
    _validate_schema(round_frame, ROUND_SUMMARY_SCHEMA)

    client_frame = pl.read_parquet(client_rounds_path)
    _validate_schema(client_frame, CLIENT_ROUNDS_SCHEMA)

    personalized_path = directory / FederatedHistoryAssetName.PERSONALIZED_ROUNDS.value
    personalized_frame = None
    if personalized_path.is_file():
        personalized_frame = pl.read_parquet(personalized_path)
        _validate_schema(personalized_frame, PERSONALIZED_ROUNDS_SCHEMA)

    rounds: list[FederatedRoundResult] = []
    for round_row in round_frame.iter_rows(named=True):
        round_number = RoundNumber(int(round_row[col.ROUND_NUMBER.value]))
        client_rows = client_frame.filter(pl.col(col.ROUND_NUMBER.value) == round_row[col.ROUND_NUMBER.value])
        client_results = tuple(
            ClientTrainingResult(
                client=ClientIdentity(coordinate.population, str(row[col.CLIENT_ID.value]), identity_kind),
                sample_count=RowCount(int(row[col.SAMPLE_COUNT.value])),
                local_loss=MetricValue(float(row[col.LOCAL_LOSS.value])),
            )
            for row in client_rows.iter_rows(named=True)
        )
        personalized_references: tuple[PersonalizedModelStateReference, ...] = ()
        if personalized_frame is not None:
            if personalized_coordinate is None:
                raise ScientificContractError(
                    "personalized training history requires personalized coordinate",
                    subject=ContractSubject.COORDINATE,
                )
            rows = personalized_frame.filter(pl.col(col.ROUND_NUMBER.value) == round_row[col.ROUND_NUMBER.value])
            personalized_references = tuple(
                PersonalizedModelStateReference(
                    coordinate=personalized_coordinate,
                    client=ClientIdentity(coordinate.population, str(row[col.CLIENT_ID.value]), identity_kind),
                    round_number=round_number,
                    local_loss=MetricValue(float(row[col.LOCAL_LOSS.value])),
                    state_checksum=Checksum(str(row[col.STATE_CHECKSUM.value])),
                    tensor_path=None,
                )
                for row in rows.iter_rows(named=True)
            )
        communication = CommunicationRecord(
            round_number=round_number,
            estimated_upload_bytes=ByteCount(int(round_row[col.UPLOAD_BYTES.value])),
            estimated_download_bytes=ByteCount(int(round_row[col.DOWNLOAD_BYTES.value])),
            estimation_basis=CommunicationEstimationMethod.SERIALIZED_MESSAGE_SIZE_ESTIMATE,
        )
        global_reference = GlobalModelStateReference(
            coordinate=coordinate,
            round_number=round_number,
            state_checksum=Checksum(str(round_row[col.GLOBAL_STATE_CHECKSUM.value])),
            tensor_path=None,
        )
        rounds.append(
            FederatedRoundResult(
                round_number=round_number,
                client_results=client_results,
                aggregate_loss=MetricValue(float(round_row[col.AGGREGATE_LOSS.value])),
                communication=communication,
                global_state_reference=global_reference,
                personalized_state_references=personalized_references,
            )
        )
    return FederatedTrainingHistory(coordinate=coordinate, rounds=tuple(rounds))
