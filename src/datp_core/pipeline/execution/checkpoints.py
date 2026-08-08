"""Federated training execution and primary checkpoint selection."""

from datp_core.core.identifiers import FeatureNameSequence
from datp_core.core.numeric import ClientCount
from datp_core.detector.checkpoints.selection import CheckpointDecision
from datp_core.detector.checkpoints.service import SelectFederatedCheckpointRequest, select_federated_primary_checkpoint
from datp_core.detector.training.engine import FederatedTrainingRequest
from datp_core.detector.training.federated_publication import TrainFederatedDetectorRequest, train_federated_detector
from datp_core.detector.training.models import CheckpointCandidate
from datp_core.pipeline.execution.context import FederatedExecutionContext, client_training_inputs
from datp_core.protocols.training import (
    BATCH_SIZE,
    CHECKPOINT_PROTOCOL,
    LEARNING_RATE,
    AutoencoderProtocol,
    resolve_single_model_federated_training_protocol,
)


def select_execution_checkpoint(
    context: FederatedExecutionContext,
    *,
    autoencoder: AutoencoderProtocol,
    feature_names: FeatureNameSequence,
) -> CheckpointCandidate:
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
                checkpoint_protocol=CHECKPOINT_PROTOCOL,
                training_seed=context.coordinate.training_seed,
                batch_size=BATCH_SIZE,
                learning_rate=LEARNING_RATE,
                split_manifest_checksum=context.split_manifest_checksum,
                output_directory=context.training_directory,
            ),
            overwrite=False,
        )
    )
    decision: CheckpointDecision = select_federated_primary_checkpoint(
        SelectFederatedCheckpointRequest(
            coordinate=context.coordinate,
            client=None,
            candidates=training.candidates,
            checkpoint_protocol=CHECKPOINT_PROTOCOL,
            preprocessing_state_set_checksum=context.preprocessing_state_set_checksum,
            split_manifest_checksum=context.split_manifest_checksum,
            held_out_metrics=None,
            attack_labels_present=False,
        )
    )
    return decision.selected
