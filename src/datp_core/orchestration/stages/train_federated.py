"""Stage: compose federated training publication across declared algorithms."""

from enum import StrEnum

from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.learning.federated.common import (
    DittoTrainingArtifacts,
    FederatedTrainingArtifacts,
    ditto_training_is_reusable,
    load_reused_ditto_artifacts,
    load_reused_federated_artifacts,
    rebase_ditto_training,
    rebase_federated_training,
    validate_federated_training_inputs,
    write_ditto_training,
    write_federated_training,
)
from datp_core.orchestration.commands.training import (
    TrainDittoRequest,
    TrainDittoStageResult,
    TrainFederatedRequest,
    TrainFederatedStageResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    FunctionalRelatedArtifactCodec,
    RelatedArtifactPublication,
    RelatedPublicationMember,
    publish_artifact,
    publish_related_artifacts,
)


class DittoPublicationMember(StrEnum):
    GLOBAL = "global"
    PERSONALIZED = "personalized"


def train_federated_stage(stage_request: TrainFederatedRequest) -> TrainFederatedStageResult:
    request = stage_request.request
    validate_federated_training_inputs(request.clients, request.autoencoder.widths[0])
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=FunctionalArtifactCodec(
                writer=write_federated_training,
                validator=federated_training_is_reusable,
                loader=load_reused_federated_artifacts,
                rebaser=rebase_federated_training,
            ),
            overwrite=stage_request.overwrite,
        )
    )
    artifacts: FederatedTrainingArtifacts = publication.value
    return TrainFederatedStageResult(
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
    )


def train_ditto_stage(stage_request: TrainDittoRequest) -> TrainDittoStageResult:
    request = stage_request.request
    validate_federated_training_inputs(request.clients, request.autoencoder.widths[0])
    publication = publish_related_artifacts(
        RelatedArtifactPublication(
            request=request,
            members=(
                RelatedPublicationMember(
                    identity=DittoPublicationMember.GLOBAL.value,
                    target=request.global_output_directory,
                ),
                RelatedPublicationMember(
                    identity=DittoPublicationMember.PERSONALIZED.value,
                    target=request.personalized_output_directory,
                ),
            ),
            codec=FunctionalRelatedArtifactCodec(
                writer=write_ditto_training,
                validator=ditto_training_is_reusable,
                loader=load_reused_ditto_artifacts,
                rebaser=rebase_ditto_training,
            ),
            overwrite=stage_request.overwrite,
        )
    )
    artifacts: DittoTrainingArtifacts = publication.value
    return TrainDittoStageResult(
        publication_status=publication.status,
        global_training=artifacts.global_training,
        global_candidates=artifacts.global_candidates,
        personalized_candidates=ClientCollection(
            tuple(ClientOwned(item.client, item.candidates) for item in artifacts.personalized_candidates)
        ),
    )
