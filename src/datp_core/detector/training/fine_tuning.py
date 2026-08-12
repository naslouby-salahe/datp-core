from dataclasses import dataclass
from pathlib import Path
from time import monotonic

from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import DatasetId, TrainingModelId
from datp_core.core.numeric import BatchSize, ElapsedSeconds, LearningRate, RoundNumber, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderModelState
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
from datp_core.detector.checkpoints.publication import load_federated_training
from datp_core.detector.training.contracts import AutoencoderProtocol, FedAvgLocalFineTuningProtocol
from datp_core.detector.training.engine import (
    SerializedStateEvidence,
    derive_fedavg_local_fine_tuning_seed,
    prepare_federated_client_data,
    serialize_model_state,
    train_client_update,
)
from datp_core.detector.training.models import ClientTrainingInput, FederatedTrainingCoordinate
from datp_core.runtime.compute import resolve_cuda_device


@dataclass(frozen=True, slots=True)
class FineTunedTerminalModel:
    client: ClientIdentity
    source_fedavg_state: AutoencoderModelState
    terminal_model_state: AutoencoderModelState
    serialized_state_evidence: SerializedStateEvidence
    wall_time: ElapsedSeconds


@dataclass(frozen=True, slots=True)
class FineTuneFedAvgClientsRequest:
    dataset: DatasetId
    source_fedavg_state: AutoencoderModelState
    clients: tuple[ClientTrainingInput, ...]
    autoencoder: AutoencoderProtocol
    protocol: FedAvgLocalFineTuningProtocol
    batch_size: BatchSize
    learning_rate: LearningRate
    training_seed: Seed


@dataclass(frozen=True, slots=True)
class PersistedFedAvgFineTuningRequest:
    dataset: DatasetId
    source_coordinate: FederatedTrainingCoordinate
    source_directory: Path
    clients: tuple[ClientTrainingInput, ...]
    autoencoder: AutoencoderProtocol
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol
    protocol: FedAvgLocalFineTuningProtocol
    batch_size: BatchSize
    learning_rate: LearningRate
    training_seed: Seed


def fine_tune_fedavg_clients(
    request: FineTuneFedAvgClientsRequest,
) -> ClientCollection[ClientIdentity, FineTunedTerminalModel]:
    if not request.clients:
        raise ScientificContractError(ErrorMessage("FedAvg local fine-tuning requires at least one client"))
    models = tuple(
        _fine_tune_client(request, client) for client in sorted(request.clients, key=lambda item: item.client)
    )
    return ClientCollection(items=tuple(ClientOwned(client=item.client, value=item) for item in models))


def fine_tune_from_persisted_fedavg(
    request: PersistedFedAvgFineTuningRequest,
) -> ClientCollection[ClientIdentity, FineTunedTerminalModel]:
    if request.source_coordinate.model is not TrainingModelId.FEDAVG_AUTOENCODER:
        raise ScientificContractError(
            ErrorMessage("fine-tuning source coordinate must be the FedAvg terminal detector")
        )
    if request.source_coordinate.training_seed != request.training_seed:
        raise ScientificContractError(
            ErrorMessage("fine-tuning source coordinate must use the requested training seed")
        )
    source = load_federated_training(
        request.source_coordinate,
        request.source_directory,
        clients=tuple(client.client for client in request.clients),
        diagnostic_snapshot_protocol=request.diagnostic_snapshot_protocol,
        autoencoder=request.autoencoder,
        batch_size=request.batch_size,
    )
    if source is None:
        raise ScientificContractError(
            ErrorMessage("FedAvg terminal scientific detector is unavailable for fine-tuning")
        )
    terminal_round = source.history.rounds[-1].round_number
    if terminal_round != RoundNumber(200):
        raise ScientificContractError(
            ErrorMessage("fine-tuning source must be the exact FedAvg terminal detector at round 200")
        )
    return fine_tune_fedavg_clients(
        FineTuneFedAvgClientsRequest(
            dataset=request.dataset,
            source_fedavg_state=source.terminal_model_state,
            clients=request.clients,
            autoencoder=request.autoencoder,
            protocol=request.protocol,
            batch_size=request.batch_size,
            learning_rate=request.learning_rate,
            training_seed=request.training_seed,
        )
    )


def _fine_tune_client(
    request: FineTuneFedAvgClientsRequest,
    client: ClientTrainingInput,
) -> FineTunedTerminalModel:
    device = resolve_cuda_device()
    started = monotonic()
    update = train_client_update(
        client_data=prepare_federated_client_data(client, request.autoencoder),
        initial_model_state=request.source_fedavg_state,
        autoencoder=request.autoencoder,
        optimizer_protocol=request.protocol.optimizer,
        learning_rate=request.learning_rate,
        batch_size=request.batch_size,
        local_epochs=request.protocol.local_epochs,
        seed=derive_fedavg_local_fine_tuning_seed(request.dataset, request.training_seed, client.client),
        device=device,
    )
    return FineTunedTerminalModel(
        client=client.client,
        source_fedavg_state=request.source_fedavg_state,
        terminal_model_state=update.model_state,
        serialized_state_evidence=serialize_model_state(update.model_state),
        wall_time=ElapsedSeconds(monotonic() - started),
    )
