from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject
from datp_core.detector.checkpoints.publication import write_federated_training as persist_federated_training
from datp_core.detector.training.contracts import FedAvgProtocol, FedProxProtocol
from datp_core.detector.training.engine import FederatedTrainingRequest, run_federated_training
from datp_core.detector.training.models import FederatedTrainingResult
from datp_core.detector.training.protocols import DECLARED_FEDAVG_LOCAL_EPOCHS

type GlobalFederatedProtocol = FedAvgProtocol | FedProxProtocol


def train_global_federated(
    request: FederatedTrainingRequest[GlobalFederatedProtocol],
) -> FederatedTrainingResult:
    _validate_protocol_binding(request)
    outcome = run_federated_training(request)
    return persist_federated_training(outcome, request.output_directory)


def _validate_protocol_binding(request: FederatedTrainingRequest[GlobalFederatedProtocol]) -> None:
    protocol = request.training_protocol

    if request.coordinate.model is not protocol.kind:
        raise ScientificContractError(
            ErrorMessage("global federated coordinate model must match its training protocol"),
            subject=request.coordinate.model,
        )

    if protocol.local_epochs not in DECLARED_FEDAVG_LOCAL_EPOCHS:
        raise ScientificContractError(
            ErrorMessage("global federated training requires a declared local epoch count"),
            subject=ContractSubject.TRAINING,
        )

    match protocol:
        case FedAvgProtocol():
            if request.coordinate.model_coefficient is not None:
                raise ScientificContractError(
                    ErrorMessage("FedAvg coordinates must not carry a model coefficient"),
                    subject=ContractSubject.COORDINATE,
                )
        case FedProxProtocol():
            if request.coordinate.model_coefficient != protocol.coefficient:
                raise ScientificContractError(
                    ErrorMessage("FedProx coordinate coefficient must match the protocol coefficient"),
                    subject=ContractSubject.COORDINATE,
                )
