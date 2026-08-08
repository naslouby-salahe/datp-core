"""Full-participation FedAvg autoencoder training."""

import torch

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ContractSubject, TrainingModelId
from datp_core.core.numeric import BatchSize, LearningRate, RoundNumber, Seed
from datp_core.detector.autoencoder import AutoencoderStateView
from datp_core.detector.checkpoints.contracts import CHECKPOINT_PROTOCOL
from datp_core.detector.training.common import (
    ClientRoundResult,
    ClientTrainingInput,
    FederatedTrainingResult,
    train_federated_global,
    train_local_model,
)
from datp_core.detector.training.contracts import AutoencoderProtocol, FederatedTrainingCoordinate, FedAvgProtocol


def train_fedavg(
    *,
    coordinate: FederatedTrainingCoordinate,
    protocol: FedAvgProtocol,
    autoencoder: AutoencoderProtocol,
    clients: tuple[ClientTrainingInput, ...],
    learning_rate: LearningRate,
    batch_size: BatchSize,
) -> FederatedTrainingResult:
    if coordinate.model is not TrainingModelId.FEDAVG_AUTOENCODER or protocol.kind is not TrainingModelId.FEDAVG_AUTOENCODER:
        raise ScientificContractError("FedAvg training requires a FedAvg coordinate and protocol", subject=ContractSubject.TRAINING)
    if coordinate.model_coefficient is not None:
        raise ScientificContractError("FedAvg cannot carry a model coefficient", subject=ContractSubject.TRAINING)
    if protocol.local_epochs.value != 1:
        raise ScientificContractError("DATP-Core FedAvg is locked to one local epoch", subject=ContractSubject.TRAINING)
    return train_federated_global(
        coordinate=coordinate,
        autoencoder=autoencoder,
        optimizer=protocol.optimizer,
        learning_rate=learning_rate,
        batch_size=batch_size,
        clients=clients,
        checkpoint_rounds=CHECKPOINT_PROTOCOL.candidates,
        local_update=_fedavg_local_update,
    )


def _fedavg_local_update(
    *,
    client_input: ClientTrainingInput,
    global_state: AutoencoderStateView,
    autoencoder: AutoencoderProtocol,
    optimizer,
    learning_rate: LearningRate,
    batch_size: BatchSize,
    device: torch.device,
    round_number: RoundNumber,
    base_seed: Seed,
) -> ClientRoundResult:
    return train_local_model(
        client_input=client_input,
        global_state=global_state,
        autoencoder=autoencoder,
        optimizer=optimizer,
        learning_rate=learning_rate,
        batch_size=batch_size,
        device=device,
        round_number=round_number,
        base_seed=base_seed,
        proximal_reference=None,
        proximal_coefficient=0.0,
    )
