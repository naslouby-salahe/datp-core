"""FedProx aggregation-side heterogeneity stress test public adapter."""

from datp_core.domain.enums import ContractSubject, TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.learning.federated.models import FederatedTrainingOutcome
from datp_core.learning.federated.training import FederatedTrainingRequest, run_federated_training
from datp_core.protocols.models import FedProxProtocol


def train_fedprox(request: FederatedTrainingRequest[FedProxProtocol]) -> FederatedTrainingOutcome:
    if request.coordinate.model is not TrainingModelId.FEDPROX_AUTOENCODER:
        raise ScientificContractError(
            "FedProx training requires the FEDPROX_AUTOENCODER coordinate",
            subject=request.coordinate.model,
        )
    if request.training_protocol.kind is not TrainingModelId.FEDPROX_AUTOENCODER:
        raise ScientificContractError(
            "FedProx training protocol must declare FEDPROX_AUTOENCODER",
            subject=request.training_protocol.kind,
        )
    if request.coordinate.model_coefficient != request.training_protocol.coefficient:
        raise ScientificContractError(
            "FedProx coordinate coefficient must match the training protocol coefficient",
            subject=ContractSubject.COORDINATE,
        )
    return run_federated_training(request)
