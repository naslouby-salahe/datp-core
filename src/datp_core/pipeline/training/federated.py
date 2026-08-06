"""Global federated training artifact publication and reuse."""

from dataclasses import dataclass

from datp_core.domain.enums import PublicationStatus
from datp_core.learning.federated.common import (
    FederatedTrainingArtifacts,
    federated_training_is_reusable,
    load_reused_federated_artifacts,
    materialize_global_federated_training,
    rebase_federated_training,
    validate_federated_training_inputs,
)
from datp_core.learning.federated.global_training import GlobalFederatedProtocol
from datp_core.learning.federated.models import CheckpointCandidate, FederatedTrainingResult
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.pipeline.publication.service import ArtifactPublication, FunctionalArtifactCodec, publish_artifact


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedDetectorRequest:
    request: FederatedTrainingRequest[GlobalFederatedProtocol]
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedDetectorResult:
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


def train_federated_detector(request: TrainFederatedDetectorRequest) -> TrainFederatedDetectorResult:
    training_request = request.request
    validate_federated_training_inputs(training_request.clients, training_request.autoencoder.widths[0])
    publication = publish_artifact(
        ArtifactPublication(
            target=training_request.output_directory,
            request=training_request,
            codec=FunctionalArtifactCodec(
                writer=materialize_global_federated_training,
                validator=federated_training_is_reusable,
                loader=load_reused_federated_artifacts,
                rebaser=rebase_federated_training,
            ),
            overwrite=request.overwrite,
        )
    )
    artifacts: FederatedTrainingArtifacts = publication.value
    return TrainFederatedDetectorResult(
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
    )
