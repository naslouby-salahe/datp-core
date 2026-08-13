from dataclasses import dataclass

from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.numeric import FeatureCount
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.common import materialize_ditto_training, validate_federated_training_inputs
from datp_core.detector.training.ditto import DittoTrainingRequest
from datp_core.detector.training.models import (
    DittoRuntimeEnvironment,
    FederatedTrainingResult,
    PersonalizedTerminalModel,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainDittoDetectorRequest:
    request: DittoTrainingRequest


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainDittoDetectorResult:
    global_training: FederatedTrainingResult
    personalized_terminal_models: ClientCollection[ClientIdentity, PersonalizedTerminalModel]
    runtime_environment: DittoRuntimeEnvironment


def train_ditto_detector(request: TrainDittoDetectorRequest) -> TrainDittoDetectorResult:
    training_request = request.request
    validate_federated_training_inputs(
        training_request.clients,
        FeatureCount(training_request.autoencoder.widths[0].value),
    )
    outcome = materialize_ditto_training(training_request)
    return TrainDittoDetectorResult(
        global_training=outcome.global_training_result,
        personalized_terminal_models=ClientCollection(
            tuple(ClientOwned(item.client, item) for item in outcome.personalized_terminal_models)
        ),
        runtime_environment=outcome.runtime_environment,
    )
