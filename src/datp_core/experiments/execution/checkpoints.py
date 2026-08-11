from datp_core.core.identifiers import FeatureNameSequence
from datp_core.core.numeric import ClientCount
from datp_core.detector.checkpoints.protocols import DIAGNOSTIC_SNAPSHOT_PROTOCOL
from datp_core.detector.training.contracts import AutoencoderProtocol
from datp_core.detector.training.engine import FederatedTrainingRequest
from datp_core.detector.training.federated_publication import TrainFederatedDetectorRequest, train_federated_detector
from datp_core.detector.training.models import FederatedTrainingResult
from datp_core.detector.training.protocols import LEARNING_RATE, resolve_single_model_federated_training_protocol
from datp_core.experiments.execution.context import (
    FederatedExecutionContext,
    client_training_inputs,
)


def train_execution_model(
    context: FederatedExecutionContext,
    *,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
) -> FederatedTrainingResult:
    protocol = resolve_single_model_federated_training_protocol(
        model=context.coordinate.model,
        coefficient=context.coordinate.model_coefficient,
    )
    training = train_federated_detector(
        TrainFederatedDetectorRequest(
            request=FederatedTrainingRequest(
                coordinate=context.coordinate,
                clients=client_training_inputs(
                    context.preprocessing.client_publications,
                    context.clients,
                    feature_names,
                ),
                population_client_count=ClientCount(len(context.clients)),
                autoencoder=autoencoder,
                training_protocol=protocol,
                diagnostic_snapshot_protocol=DIAGNOSTIC_SNAPSHOT_PROTOCOL,
                training_seed=context.coordinate.training_seed,
                batch_size=context.batch_size,
                learning_rate=LEARNING_RATE,
                output_directory=context.training_directory,
                client_data_residency=context.client_data_residency,
            ),
        )
    )
    return training.training
