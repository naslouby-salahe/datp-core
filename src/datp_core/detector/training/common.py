from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.numeric import FeatureCount
from datp_core.detector.training.ditto import DittoTrainingRequest, train_ditto
from datp_core.detector.training.engine import FederatedTrainingRequest
from datp_core.detector.training.federated import GlobalFederatedProtocol, train_global_federated
from datp_core.detector.training.models import ClientTrainingInput, DittoTrainingOutcome, FederatedTrainingResult


def validate_federated_training_inputs(
    clients: tuple[ClientTrainingInput, ...],
    autoencoder_width: FeatureCount,
) -> None:
    if not clients:
        raise ScientificContractError(ErrorMessage("federated training requires client inputs"))
    feature_names = clients[0].feature_names
    if autoencoder_width.value != len(feature_names):
        raise ScientificContractError(ErrorMessage("autoencoder input width must match the transformed feature schema"))
    for client in clients[1:]:
        if client.feature_names != feature_names:
            raise ScientificContractError(ErrorMessage("federated clients must share one transformed feature schema"))


def materialize_global_federated_training(
    request: FederatedTrainingRequest[GlobalFederatedProtocol],
) -> FederatedTrainingResult:
    return train_global_federated(request)


def materialize_ditto_training(request: DittoTrainingRequest) -> DittoTrainingOutcome:
    return train_ditto(request)
