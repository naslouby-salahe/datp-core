"""Stage: compose federated scoring with shared publication infrastructure."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from datp_core.domain.enums import PublicationStatus, StageOperationId
from datp_core.domain.values import BatchSize, Checksum, FeatureNameSequence
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
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


@dataclass(slots=True, eq=False)
class ScoreFederatedRequest:
    checkpoint: CheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    clients: tuple[ClientScoringInput, ...]
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_set_checksum: Checksum
    split_manifest_checksum: Checksum
    overwrite: bool


@dataclass(frozen=True, slots=True)
class ScoreFederatedStageResult:
    stage: ClassVar[StageOperationId] = StageOperationId.SCORE_FEDERATED
    publication_status: PublicationStatus
    result: ScoreGenerationResult


def score_federated_stage(request: ScoreFederatedRequest) -> ScoreFederatedStageResult:
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=FunctionalArtifactCodec(
                writer=lambda stage_request, directory: write_federated_scores(
                    _generation_request(stage_request, directory),
                    directory,
                    resolve_cuda_device(),
                ),
                validator=lambda stage_request, directory: federated_scoring_is_reusable(
                    _generation_request(stage_request, directory),
                    directory,
                ),
                loader=lambda stage_request, directory: load_reused_federated_scores(
                    _generation_request(stage_request, directory),
                    directory,
                ),
                rebaser=rebase_federated_scores,
            ),
            overwrite=request.overwrite,
            complete_marker=FederatedScoreAssetName.COMPLETE.value,
        )
    )
    return ScoreFederatedStageResult(
        publication_status=publication.status,
        result=publication.value,
    )


def _generation_request(
    request: ScoreFederatedRequest,
    directory: Path,
) -> ScoreGenerationRequest:
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
