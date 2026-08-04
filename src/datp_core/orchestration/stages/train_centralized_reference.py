"""Stage: compose independent centralized autoencoder training publication."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import polars as pl

from datp_core.centralized_reference.checkpointing import CentralizedCheckpointCandidate
from datp_core.centralized_reference.training import (
    CentralizedArtifactName,
    CentralizedTrainingCoordinate,
    CentralizedTrainingResult,
    declared_centralized_training_values,
    require_no_hidden_scientific_defaults,
)
from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import Checksum, FeatureNameSequence, Seed, checksum_file
from datp_core.learning.centralized.adapter import (
    CentralizedTrainingArtifacts,
    CentralizedTrainingPublicationRequest,
    centralized_training_is_reusable,
    load_reused_centralized_training,
    rebase_centralized_training,
    validate_centralized_training_request,
    write_centralized_training,
)
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol


@dataclass(slots=True, eq=False)
class TrainCentralizedReferenceRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    split_manifest_checksum: Checksum
    output_directory: Path
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    checkpoint_protocol: CheckpointProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True)
class TrainCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_CENTRALIZED_REFERENCE
    publication_status: PublicationStatus
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    complete_digest: Checksum


def train_centralized_reference_stage(
    request: TrainCentralizedReferenceRequest,
) -> TrainCentralizedReferenceResult:
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
    return TrainCentralizedReferenceResult(
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
        complete_digest=checksum_file(request.output_directory / CentralizedArtifactName.COMPLETE),
    )
