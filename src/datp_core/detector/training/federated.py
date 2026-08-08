from datp_core.detector.checkpoints.publication import write_federated_training as persist_federated_training
from datp_core.detector.training.engine import FederatedTrainingRequest, run_federated_training
from datp_core.detector.training.models import FederatedTrainingOutcome
from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.protocols.training import FEDAVG_LOCAL_EPOCHS, FedAvgProtocol, FedProxProtocol

type GlobalFederatedProtocol = FedAvgProtocol | FedProxProtocol


def train_global_federated(
    request: FederatedTrainingRequest[GlobalFederatedProtocol],
) -> FederatedTrainingOutcome:
    _validate_protocol_binding(request)
    outcome = run_federated_training(request)
    return persist_federated_training(outcome, request.output_directory)


def _validate_protocol_binding(request: FederatedTrainingRequest[GlobalFederatedProtocol]) -> None:
    protocol = request.training_protocol

    if request.coordinate.model is not protocol.kind:
        raise ScientificContractError(
            "global federated coordinate model must match its training protocol",
            subject=request.coordinate.model,
        )

    if protocol.local_epochs != FEDAVG_LOCAL_EPOCHS:
        raise ScientificContractError(
            "global federated training requires the locked single local epoch",
            subject=ContractSubject.TRAINING,
        )

    match protocol:
        case FedAvgProtocol():
            if request.coordinate.model_coefficient is not None:
                raise ScientificContractError(
                    "FedAvg coordinates must not carry a model coefficient",
                    subject=ContractSubject.COORDINATE,
                )
        case FedProxProtocol():
            if request.coordinate.model_coefficient != protocol.coefficient:
                raise ScientificContractError(
                    "FedProx coordinate coefficient must match the protocol coefficient",
                    subject=ContractSubject.COORDINATE,
                )
