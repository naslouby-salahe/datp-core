"""Full-participation FedProx autoencoder training."""

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
from datp_core.detector.training.contracts import (
    AutoencoderProtocol,
    FederatedTrainingCoordinate,
    FedProxProtocol,
    OptimizerProtocol,
)


def train_fedprox(
    *,
    coordinate: FederatedTrainingCoordinate,
    protocol: FedProxProtocol,
    autoencoder: AutoencoderProtocol,
    clients: tuple[ClientTrainingInput, ...],
    learning_rate: LearningRate,
    batch_size: BatchSize,
) -> FederatedTrainingResult:
    if (
        coordinate.model is not TrainingModelId.FEDPROX_AUTOENCODER
        or protocol.kind is not TrainingModelId.FEDPROX_AUTOENCODER
    ):
        raise ScientificContractError(
            "FedProx training requires a FedProx coordinate and protocol", subject=ContractSubject.TRAINING
        )
    if coordinate.model_coefficient != protocol.coefficient:
        raise ScientificContractError(
            "FedProx coordinate coefficient must match the selected protocol", subject=ContractSubject.TRAINING
        )
    if protocol.local_epochs.value != 1:
        raise ScientificContractError(
            "DATP-Core FedProx is locked to one local epoch", subject=ContractSubject.TRAINING
        )

    def local_update(
        *,
        client_input: ClientTrainingInput,
        global_state: AutoencoderStateView,
        autoencoder: AutoencoderProtocol,
        optimizer: OptimizerProtocol,
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
            proximal_reference=global_state,
            proximal_coefficient=protocol.coefficient.value,
        )

    return train_federated_global(
        coordinate=coordinate,
        autoencoder=autoencoder,
        optimizer=protocol.optimizer,
        learning_rate=learning_rate,
        batch_size=batch_size,
        clients=clients,
        checkpoint_rounds=CHECKPOINT_PROTOCOL.candidates,
        local_update=local_update,
    )
