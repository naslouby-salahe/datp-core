"""FedAvg core detector training public adapter."""

from datp_core.domain.enums import ContractSubject, TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.learning.federated.models import FederatedTrainingOutcome
from datp_core.learning.federated.training import FederatedTrainingRequest, run_federated_training


def train_fedavg(request: FederatedTrainingRequest) -> FederatedTrainingOutcome:
    """Train the FedAvg core detector to the declared maximum round."""
    if request.coordinate.model != TrainingModelId.FEDAVG_AUTOENCODER:
        raise ScientificContractError(
            "FedAvg training requires the FEDAVG_AUTOENCODER coordinate",
            subject=request.coordinate.model,
        )
    if request.training_protocol.kind is not TrainingModelId.FEDAVG_AUTOENCODER:
        raise ScientificContractError(
            "FedAvg training protocol must declare FEDAVG_AUTOENCODER",
            subject=request.training_protocol.kind,
        )
    if request.coordinate.model_coefficient is not None:
        raise ScientificContractError(
            "FedAvg coordinates carry no model coefficient",
            subject=ContractSubject.TRAINING,
        )
    return run_federated_training(request, proximal_coefficient=None)
