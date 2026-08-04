"""Stage: compose pooled scoring with shared publication infrastructure."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

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
from datp_core.domain.enums import ContractSubject, PublicationStatus, StageOperationId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import BatchSize, Checksum, FeatureNameSequence, checksum_file
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    FunctionalArtifactCodec,
    publish_artifact,
)
from datp_core.protocols.models import AutoencoderProtocol


@dataclass(slots=True, eq=False)
class ScoreCentralizedReferenceRequest:
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


@dataclass(frozen=True, slots=True)
class ScoreCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.SCORE_CENTRALIZED_REFERENCE
    publication_status: PublicationStatus
    scoring: CentralizedScoringResult
    complete_digest: Checksum


def score_centralized_reference_stage(
    request: ScoreCentralizedReferenceRequest,
) -> ScoreCentralizedReferenceResult:
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
                writer=lambda stage_request, directory: write_centralized_scoring(
                    _scoring_request(stage_request, directory),
                    directory,
                ),
                validator=lambda stage_request, directory: centralized_scoring_is_reusable(
                    _scoring_request(stage_request, directory),
                    directory,
                ),
                loader=lambda stage_request, directory: load_reused_centralized_scoring(
                    _scoring_request(stage_request, directory),
                    directory,
                ),
                rebaser=rebase_centralized_scoring,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedScoreAssetName.COMPLETE,
        )
    )
    return ScoreCentralizedReferenceResult(
        publication_status=publication.status,
        scoring=publication.value,
        complete_digest=checksum_file(request.output_directory / CentralizedScoreAssetName.COMPLETE),
    )


def _scoring_request(
    request: ScoreCentralizedReferenceRequest,
    directory: Path,
) -> CentralizedScoringRequest:
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
