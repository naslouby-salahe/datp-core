"""Ditto personalized detector training publication."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.artifacts.repositories.publication import (
    FunctionalRelatedArtifactCodec,
    RelatedArtifactPublication,
    RelatedPublicationMember,
    publish_related_artifacts,
)
from datp_core.core.contracts import ClientCollection, ClientOwned
from datp_core.core.identifiers import PublicationStatus
from datp_core.data.populations.contracts import ClientIdentity
from datp_core.detector.training.common import (
    DittoTrainingArtifacts,
    ditto_training_is_reusable,
    load_reused_ditto_artifacts,
    rebase_ditto_training,
    validate_federated_training_inputs,
    write_ditto_training,
)
from datp_core.detector.training.ditto import DittoTrainingRequest
from datp_core.detector.training.models import CheckpointCandidate, FederatedTrainingResult


class DittoPublicationMember(StrEnum):
    GLOBAL = "global"
    PERSONALIZED = "personalized"


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainDittoDetectorRequest:
    request: DittoTrainingRequest
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainDittoDetectorResult:
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: ClientCollection[ClientIdentity, tuple[CheckpointCandidate, ...]]


def train_ditto_detector(request: TrainDittoDetectorRequest) -> TrainDittoDetectorResult:
    training_request = request.request
    validate_federated_training_inputs(training_request.clients, training_request.autoencoder.widths[0])
    publication = publish_related_artifacts(
        RelatedArtifactPublication(
            request=training_request,
            members=(
                RelatedPublicationMember(
                    identity=DittoPublicationMember.GLOBAL.value,
                    target=training_request.global_output_directory,
                ),
                RelatedPublicationMember(
                    identity=DittoPublicationMember.PERSONALIZED.value,
                    target=training_request.personalized_output_directory,
                ),
            ),
            codec=FunctionalRelatedArtifactCodec(
                writer=write_ditto_training,
                validator=ditto_training_is_reusable,
                loader=load_reused_ditto_artifacts,
                rebaser=rebase_ditto_training,
            ),
            overwrite=request.overwrite,
        )
    )
    artifacts: DittoTrainingArtifacts = publication.value
    return TrainDittoDetectorResult(
        publication_status=publication.status,
        global_training=artifacts.global_training,
        global_candidates=artifacts.global_candidates,
        personalized_candidates=ClientCollection(
            tuple(ClientOwned(item.client, item.candidates) for item in artifacts.personalized_candidates)
        ),
    )
