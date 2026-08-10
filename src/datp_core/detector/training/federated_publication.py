from dataclasses import dataclass

from datp_core.core.numeric import FeatureCount
from datp_core.detector.training.common import materialize_global_federated_training, validate_federated_training_inputs
from datp_core.detector.training.engine import FederatedTrainingRequest
from datp_core.detector.training.federated import GlobalFederatedProtocol
from datp_core.detector.training.models import FederatedTrainingResult


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedDetectorRequest:
    request: FederatedTrainingRequest[GlobalFederatedProtocol]


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedDetectorResult:
    training: FederatedTrainingResult


def train_federated_detector(request: TrainFederatedDetectorRequest) -> TrainFederatedDetectorResult:
    training_request = request.request
    validate_federated_training_inputs(
        training_request.clients,
        FeatureCount(training_request.autoencoder.widths[0].value),
    )
    return TrainFederatedDetectorResult(training=materialize_global_federated_training(training_request))
