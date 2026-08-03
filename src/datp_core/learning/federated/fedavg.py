"""FedAvg public training adapter."""

from datp_core.domain.enums import ContractSubject, TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.learning.federated.checkpointing import publish_federated_training
from datp_core.learning.federated.models import FederatedTrainingOutcome
from datp_core.learning.federated.training import (
    FederatedTrainingRequest,
    run_federated_training,
)
from datp_core.protocols.models import FedAvgProtocol


def train_fedavg(
    request: FederatedTrainingRequest[FedAvgProtocol],
) -> FederatedTrainingOutcome:
    if request.coordinate.model is not TrainingModelId.FEDAVG_AUTOENCODER:
        raise ScientificContractError(
            "FedAvg requires the FEDAVG_AUTOENCODER coordinate",
            subject=request.coordinate.model,
        )
    if request.training_protocol.kind is not TrainingModelId.FEDAVG_AUTOENCODER:
        raise ScientificContractError(
            "FedAvg protocol kind must be FEDAVG_AUTOENCODER",
            subject=request.training_protocol.kind,
        )
    if request.training_protocol.local_epochs.value != 1:
        raise ScientificContractError(
            "FedAvg requires exactly one local epoch",
            subject=ContractSubject.TRAINING,
        )
    execution = run_federated_training(request)
    return publish_federated_training(
        execution,
        request.output_directory,
    )
