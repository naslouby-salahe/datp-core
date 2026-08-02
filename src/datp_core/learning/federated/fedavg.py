"""FedAvg core detector training public adapter."""

from datp_core.domain.enums import TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.learning.federated.models import FederatedTrainingOutcome
from datp_core.learning.federated.training import FederatedTrainingRequest, run_federated_training
from datp_core.protocols.models import FedAvgProtocol


def train_fedavg(request: FederatedTrainingRequest[FedAvgProtocol]) -> FederatedTrainingOutcome:
    if request.coordinate.model is not TrainingModelId.FEDAVG_AUTOENCODER:
        raise ScientificContractError(
            "FedAvg training requires the FEDAVG_AUTOENCODER coordinate",
            subject=request.coordinate.model,
        )
    if request.training_protocol.kind is not TrainingModelId.FEDAVG_AUTOENCODER:
        raise ScientificContractError(
            "FedAvg training protocol must declare FEDAVG_AUTOENCODER",
            subject=request.training_protocol.kind,
        )
    return run_federated_training(request)
