"""Federated and centralized reconstruction-score publication."""

from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.centralized_reference.checkpointing import CentralizedCheckpointCandidate
from datp_core.centralized_reference.scoring import (
    CentralizedScoreAssetName,
    CentralizedScoringRequest,
    CentralizedScoringResult,
    centralized_scoring_is_reusable,
    load_reused_centralized_scoring,
    rebase_centralized_scoring,
    write_centralized_scoring,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import ContractSubject, PublicationStatus
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import BatchSize, Checksum, FeatureNameSequence
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.publication.codec import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.runtime.compute import resolve_cuda_device
from datp_core.scoring.generation import (
    ClientScoringInput,
    FederatedScoreAssetName,
    ScoreGenerationRequest,
    federated_scoring_is_reusable,
    load_reused_federated_scores,
    rebase_federated_scores,
    write_federated_scores,
)
from datp_core.scoring.models import ScoreGenerationResult


@dataclass(slots=True, eq=False, kw_only=True)
class GenerateFederatedScoresRequest:
    checkpoint: CheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateFederatedScoresResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    result: ScoreGenerationResult


@dataclass(slots=True, eq=False, kw_only=True)
class GenerateCentralizedScoresRequest:
    coordinate: CentralizedTrainingCoordinate
    checkpoint: CentralizedCheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_checksum: Checksum
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class GenerateCentralizedScoresResult:
    stage: PipelineStage
    publication_status: PublicationStatus
    scoring: CentralizedScoringResult
    complete_digest: Checksum


def generate_federated_scores(request: GenerateFederatedScoresRequest) -> GenerateFederatedScoresResult:
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=FunctionalArtifactCodec(
                writer=lambda item, directory: write_federated_scores(
                    _federated_request(item, directory), directory, resolve_cuda_device()
                ),
                validator=lambda item, directory: federated_scoring_is_reusable(
                    _federated_request(item, directory), directory
                ),
                loader=lambda item, directory: load_reused_federated_scores(
                    _federated_request(item, directory), directory
                ),
                rebaser=rebase_federated_scores,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedScoreAssetName.COMPLETE.value,
        )
    )
    return GenerateFederatedScoresResult(
        stage=PipelineStage.GENERATE_SCORES,
        publication_status=publication.status,
        result=publication.value,
    )


def generate_centralized_scores(request: GenerateCentralizedScoresRequest) -> GenerateCentralizedScoresResult:
    if request.checkpoint.coordinate != request.coordinate:
        raise ScientificContractError(
            "score stage checkpoint coordinate mismatch",
            subject=ContractSubject.COORDINATE,
        )
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=FunctionalArtifactCodec(
                writer=lambda item, directory: write_centralized_scoring(
                    _centralized_request(item, directory), directory
                ),
                validator=lambda item, directory: centralized_scoring_is_reusable(
                    _centralized_request(item, directory), directory
                ),
                loader=lambda item, directory: load_reused_centralized_scoring(
                    _centralized_request(item, directory), directory
                ),
                rebaser=rebase_centralized_scoring,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedScoreAssetName.COMPLETE,
        )
    )
    return GenerateCentralizedScoresResult(
        stage=PipelineStage.GENERATE_SCORES,
        publication_status=publication.status,
        scoring=publication.value,
        complete_digest=publication.complete_digest,
    )


def _federated_request(request: GenerateFederatedScoresRequest, directory: Path) -> ScoreGenerationRequest:
    return ScoreGenerationRequest(
        checkpoint=request.checkpoint,
        autoencoder=request.autoencoder,
        feature_names=request.feature_names,
        clients=request.clients,
        batch_size=request.batch_size,
        output_directory=directory,
        preprocessing_state_set_checksum=request.preprocessing_state_set_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
    )


def _centralized_request(request: GenerateCentralizedScoresRequest, directory: Path) -> CentralizedScoringRequest:
    return CentralizedScoringRequest(
        coordinate=request.coordinate,
        checkpoint=request.checkpoint,
        autoencoder=request.autoencoder,
        feature_names=request.feature_names,
        calibration_features=request.calibration_features,
        evaluation_features=request.evaluation_features,
        batch_size=request.batch_size,
        output_directory=directory,
        preprocessing_state_checksum=request.preprocessing_state_checksum,
    )
