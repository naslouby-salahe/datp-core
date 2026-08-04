"""FedProx public training adapter with a proximal client-local objective."""

from datp_core.domain.enums import ContractSubject, TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.learning.federated.checkpoints.publication import write_federated_training
from datp_core.learning.federated.models import FederatedTrainingOutcome
from datp_core.learning.federated.training import FederatedTrainingRequest, run_federated_training
from datp_core.protocols.models import FedProxProtocol


def train_fedprox(request: FederatedTrainingRequest[FedProxProtocol]) -> FederatedTrainingOutcome:
    if request.coordinate.model is not TrainingModelId.FEDPROX_AUTOENCODER:
        raise ScientificContractError(
            "FedProx requires the FEDPROX_AUTOENCODER coordinate",
            subject=request.coordinate.model,
        )
    if request.training_protocol.kind is not TrainingModelId.FEDPROX_AUTOENCODER:
        raise ScientificContractError(
            "FedProx protocol kind must be FEDPROX_AUTOENCODER",
            subject=request.training_protocol.kind,
        )
    if request.training_protocol.local_epochs.value != 1:
        raise ScientificContractError(
            "FedProx requires exactly one local epoch",
            subject=ContractSubject.TRAINING,
        )
    if request.coordinate.model_coefficient != request.training_protocol.coefficient:
        raise ScientificContractError(
            "FedProx coordinate coefficient must match the protocol coefficient",
            subject=ContractSubject.COORDINATE,
        )
    return write_federated_training(run_federated_training(request), request.output_directory)
