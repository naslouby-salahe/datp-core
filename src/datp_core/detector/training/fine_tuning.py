from dataclasses import dataclass

from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.numeric import BatchSize, LearningRate, Seed
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.autoencoder import AutoencoderModelState
from datp_core.detector.training.contracts import AutoencoderProtocol, FedAvgLocalFineTuningProtocol
from datp_core.detector.training.engine import (
    derive_fedavg_local_fine_tuning_seed,
    prepare_federated_client_data,
    train_client_update,
)
from datp_core.detector.training.models import ClientTrainingInput
from datp_core.runtime.compute import resolve_cuda_device


@dataclass(frozen=True, slots=True)
class FineTunedTerminalModel:
    client: ClientIdentity
    source_fedavg_state: AutoencoderModelState
    terminal_model_state: AutoencoderModelState


@dataclass(frozen=True, slots=True)
class FineTuneFedAvgClientsRequest:
    source_fedavg_state: AutoencoderModelState
    clients: tuple[ClientTrainingInput, ...]
    autoencoder: AutoencoderProtocol
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


def _fine_tune_client(
    request: FineTuneFedAvgClientsRequest,
    client: ClientTrainingInput,
) -> FineTunedTerminalModel:
    device = resolve_cuda_device()
    update = train_client_update(
        client_data=prepare_federated_client_data(client, request.autoencoder),
        initial_model_state=request.source_fedavg_state,
        autoencoder=request.autoencoder,
        optimizer_protocol=request.protocol.optimizer,
        learning_rate=request.learning_rate,
        batch_size=request.batch_size,
        local_epochs=request.protocol.local_epochs,
        seed=derive_fedavg_local_fine_tuning_seed(request.training_seed, client.client),
        device=device,
    )
    return FineTunedTerminalModel(
        client=client.client,
        source_fedavg_state=request.source_fedavg_state,
        terminal_model_state=update.model_state,
    )
