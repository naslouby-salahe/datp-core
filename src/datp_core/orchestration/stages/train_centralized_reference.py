"""Stage: compose independent centralized autoencoder training publication."""

from datp_core.centralized_reference.training import (
    CentralizedArtifactName,
    declared_centralized_training_values,
    require_no_hidden_scientific_defaults,
)
from datp_core.learning.centralized.adapter import (
    CentralizedTrainingArtifacts,
    CentralizedTrainingPublicationRequest,
    centralized_training_is_reusable,
    load_reused_centralized_training,
    rebase_centralized_training,
    validate_centralized_training_request,
    write_centralized_training,
)
from datp_core.orchestration.commands.training import (
    TrainCentralizedReferenceRequest as _TrainCentralizedReferenceRequest,
)
from datp_core.orchestration.commands.training import (
    TrainCentralizedReferenceResult as _TrainCentralizedReferenceResult,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)


def train_centralized_reference_stage(
    request: _TrainCentralizedReferenceRequest,
) -> _TrainCentralizedReferenceResult:
    require_no_hidden_scientific_defaults()
    training_protocol, _declared_autoencoder, learning_rate, batch_size, weight_decay = (
        declared_centralized_training_values()
    )
    publication_request = CentralizedTrainingPublicationRequest(
        coordinate=request.coordinate,
        training_features=request.training_features,
        feature_names=request.feature_names,
        preprocessing_state=request.preprocessing_state,
        split_manifest_checksum=request.split_manifest_checksum,
        output_directory=request.output_directory,
        training_seed=request.training_seed,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        training_protocol=training_protocol,
        learning_rate=learning_rate,
        batch_size=batch_size,
        weight_decay=weight_decay,
    )
    validate_centralized_training_request(publication_request)
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_training,
                validator=centralized_training_is_reusable,
                loader=load_reused_centralized_training,
                rebaser=rebase_centralized_training,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedArtifactName.COMPLETE,
        )
    )
    artifacts: CentralizedTrainingArtifacts = publication.value
    return _TrainCentralizedReferenceResult(
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
        complete_digest=publication.complete_digest,
    )
