"""Federated and centralized detector training publication."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.centralized_reference.checkpointing import CentralizedCheckpointCandidate
from datp_core.centralized_reference.training import (
    CentralizedArtifactName,
    CentralizedTrainingCoordinate,
    CentralizedTrainingResult,
    declared_centralized_training_values,
    require_no_hidden_scientific_defaults,
)
from datp_core.domain.contracts import ClientCollection, ClientOwned
from datp_core.domain.enums import PublicationStatus
from datp_core.domain.values import Checksum, FeatureNameSequence, Seed
from datp_core.learning.centralized.adapter import (
    CentralizedTrainingArtifacts,
    CentralizedTrainingPublicationRequest,
    centralized_training_is_reusable,
    load_reused_centralized_training,
    rebase_centralized_training,
    validate_centralized_training_request,
    write_centralized_training,
)
from datp_core.learning.federated.common import (
    DittoTrainingArtifacts,
    FederatedTrainingArtifacts,
    GlobalFederatedProtocol,
    ditto_training_is_reusable,
    federated_training_is_reusable,
    load_reused_ditto_artifacts,
    load_reused_federated_artifacts,
    rebase_ditto_training,
    rebase_federated_training,
    validate_federated_training_inputs,
    write_ditto_training,
    write_federated_training,
)
from datp_core.learning.federated.ditto import DittoTrainingRequest
from datp_core.learning.federated.models import CheckpointCandidate, FederatedTrainingResult
from datp_core.learning.federated.training import FederatedTrainingRequest
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    FunctionalRelatedArtifactCodec,
    RelatedArtifactPublication,
    RelatedPublicationMember,
    publish_artifact,
    publish_related_artifacts,
)
from datp_core.populations.models import ClientIdentity
from datp_core.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol


class DittoPublicationMember(StrEnum):
    GLOBAL = "global"
    PERSONALIZED = "personalized"


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedDetectorRequest:
    request: FederatedTrainingRequest[GlobalFederatedProtocol]
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainDittoDetectorRequest:
    request: DittoTrainingRequest
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainFederatedDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    training: FederatedTrainingResult
    candidates: tuple[CheckpointCandidate, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainDittoDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    global_training: FederatedTrainingResult
    global_candidates: tuple[CheckpointCandidate, ...]
    personalized_candidates: ClientCollection[ClientIdentity, tuple[CheckpointCandidate, ...]]


@dataclass(slots=True, eq=False, kw_only=True)
class TrainCentralizedDetectorRequest:
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


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainCentralizedDetectorResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    complete_digest: Checksum


def train_federated_detector(request: TrainFederatedDetectorRequest) -> TrainFederatedDetectorResult:
    training_request = request.request
    validate_federated_training_inputs(training_request.clients, training_request.autoencoder.widths[0])
    publication = publish_artifact(
        ArtifactPublication(
            target=training_request.output_directory,
            request=training_request,
            codec=FunctionalArtifactCodec(
                writer=write_federated_training,
                validator=federated_training_is_reusable,
                loader=load_reused_federated_artifacts,
                rebaser=rebase_federated_training,
            ),
            overwrite=request.overwrite,
        )
    )
    artifacts: FederatedTrainingArtifacts = publication.value
    return TrainFederatedDetectorResult(
        stage=PipelineStage.TRAIN_DETECTOR,
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
    )


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
        stage=PipelineStage.TRAIN_DETECTOR,
        publication_status=publication.status,
        global_training=artifacts.global_training,
        global_candidates=artifacts.global_candidates,
        personalized_candidates=ClientCollection(
            tuple(ClientOwned(item.client, item.candidates) for item in artifacts.personalized_candidates)
        ),
    )


def train_centralized_detector(request: TrainCentralizedDetectorRequest) -> TrainCentralizedDetectorResult:
    require_no_hidden_scientific_defaults()
    training_protocol, _, learning_rate, batch_size, weight_decay = declared_centralized_training_values()
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
    return TrainCentralizedDetectorResult(
        stage=PipelineStage.TRAIN_DETECTOR,
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
        complete_digest=publication.complete_digest,
    )
