"""Stage: score pooled partitions with the selected centralized checkpoint."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import polars as pl

from datp_core.centralized_reference.checkpointing import CentralizedCheckpointCandidate
from datp_core.centralized_reference.scoring import (
    CentralizedScoreAssetName,
    CentralizedScoringRequest,
    CentralizedScoringResult,
    PooledScoreArtifact,
    score_artifact_set_checksum,
    score_centralized_reference,
)
from datp_core.centralized_reference.training import CentralizedTrainingCoordinate
from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    PublicationStatus,
    SerializationFormat,
    StageOperationId,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureCount,
    FeatureNameSequence,
    RowCount,
    checksum_file,
    checksum_text,
)
from datp_core.pipeline.publication.codec import ArtifactPublication, publish_artifact
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


@dataclass(frozen=True, slots=True)
class _CentralizedScoringCodec:
    def write(
        self,
        request: ScoreCentralizedReferenceRequest,
        directory: Path,
    ) -> CentralizedScoringResult:
        scoring = score_centralized_reference(
            CentralizedScoringRequest(
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
        )
        (directory / CentralizedScoreAssetName.COMPLETE).write_text(
            score_artifact_set_checksum(scoring).value,
            encoding="utf-8",
        )
        return scoring

    def validate(self, request: ScoreCentralizedReferenceRequest, directory: Path) -> bool:
        return _is_reusable(directory, request)

    def load(
        self,
        request: ScoreCentralizedReferenceRequest,
        directory: Path,
    ) -> CentralizedScoringResult:
        return _load_reused_scores(request, directory)

    def rebase(
        self,
        result: CentralizedScoringResult,
        directory: Path,
    ) -> CentralizedScoringResult:
        return _rebase_scoring(result, request_directory=directory)


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
            codec=_CentralizedScoringCodec(),
            overwrite=request.overwrite,
            complete_marker=CentralizedScoreAssetName.COMPLETE,
        )
    )
    return ScoreCentralizedReferenceResult(
        publication_status=publication.status,
        scoring=publication.value,
        complete_digest=checksum_file(request.output_directory / CentralizedScoreAssetName.COMPLETE),
    )


def _is_reusable(directory: Path, request: ScoreCentralizedReferenceRequest) -> bool:
    complete = directory / CentralizedScoreAssetName.COMPLETE
    calibration = directory / CentralizedScoreAssetName.CALIBRATION_SCORES
    evaluation = directory / CentralizedScoreAssetName.EVALUATION_SCORES
    if not (complete.is_file() and calibration.is_file() and evaluation.is_file()):
        return False
    try:
        expected = checksum_text(
            f"{checksum_file(calibration).value}|{checksum_file(evaluation).value}|"
            f"{request.checkpoint.tensor_checksum.value}"
        )
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except (OSError, ValueError):
        return False


def _score_artifact_pair(
    request: ScoreCentralizedReferenceRequest,
    directory: Path,
    *,
    calibration_row_count: RowCount,
    evaluation_row_count: RowCount,
) -> tuple[PooledScoreArtifact, PooledScoreArtifact]:
    calibration_path = directory / CentralizedScoreAssetName.CALIBRATION_SCORES
    evaluation_path = directory / CentralizedScoreAssetName.EVALUATION_SCORES
    return (
        PooledScoreArtifact(
            coordinate=request.coordinate,
            partition_role=PartitionRole.CALIBRATION,
            checkpoint_round=request.checkpoint.round_number,
            checkpoint_checksum=request.checkpoint.tensor_checksum,
            path=calibration_path,
            checksum=checksum_file(calibration_path),
            row_count=calibration_row_count,
            feature_count=FeatureCount(len(request.feature_names)),
            serialization_format=SerializationFormat.PARQUET,
        ),
        PooledScoreArtifact(
            coordinate=request.coordinate,
            partition_role=PartitionRole.EVALUATION,
            checkpoint_round=request.checkpoint.round_number,
            checkpoint_checksum=request.checkpoint.tensor_checksum,
            path=evaluation_path,
            checksum=checksum_file(evaluation_path),
            row_count=evaluation_row_count,
            feature_count=FeatureCount(len(request.feature_names)),
            serialization_format=SerializationFormat.PARQUET,
        ),
    )


def _load_reused_scores(
    request: ScoreCentralizedReferenceRequest,
    directory: Path,
) -> CentralizedScoringResult:
    calibration_frame = pl.read_parquet(directory / CentralizedScoreAssetName.CALIBRATION_SCORES)
    evaluation_frame = pl.read_parquet(directory / CentralizedScoreAssetName.EVALUATION_SCORES)
    calibration, evaluation = _score_artifact_pair(
        request,
        directory,
        calibration_row_count=RowCount(calibration_frame.height),
        evaluation_row_count=RowCount(evaluation_frame.height),
    )
    return CentralizedScoringResult(
        calibration_scores=calibration,
        evaluation_scores=evaluation,
        model_tensor_checksum=request.checkpoint.tensor_checksum,
        preprocessing_state_checksum=request.preprocessing_state_checksum,
    )


def _rebase_scoring(
    scoring: CentralizedScoringResult,
    *,
    request_directory: Path,
) -> CentralizedScoringResult:
    calibration_path = request_directory / CentralizedScoreAssetName.CALIBRATION_SCORES
    evaluation_path = request_directory / CentralizedScoreAssetName.EVALUATION_SCORES
    if not calibration_path.is_file() or not evaluation_path.is_file():
        raise ArtifactIntegrityError(
            "published score partitions missing after atomic replace",
            subject=ContractSubject.SCORES,
        )
    calibration = PooledScoreArtifact(
        coordinate=scoring.calibration_scores.coordinate,
        partition_role=PartitionRole.CALIBRATION,
        checkpoint_round=scoring.calibration_scores.checkpoint_round,
        checkpoint_checksum=scoring.calibration_scores.checkpoint_checksum,
        path=calibration_path,
        checksum=checksum_file(calibration_path),
        row_count=scoring.calibration_scores.row_count,
        feature_count=scoring.calibration_scores.feature_count,
        serialization_format=SerializationFormat.PARQUET,
    )
    evaluation = PooledScoreArtifact(
        coordinate=scoring.evaluation_scores.coordinate,
        partition_role=PartitionRole.EVALUATION,
        checkpoint_round=scoring.evaluation_scores.checkpoint_round,
        checkpoint_checksum=scoring.evaluation_scores.checkpoint_checksum,
        path=evaluation_path,
        checksum=checksum_file(evaluation_path),
        row_count=scoring.evaluation_scores.row_count,
        feature_count=scoring.evaluation_scores.feature_count,
        serialization_format=SerializationFormat.PARQUET,
    )
    return CentralizedScoringResult(
        calibration_scores=calibration,
        evaluation_scores=evaluation,
        model_tensor_checksum=scoring.model_tensor_checksum,
        preprocessing_state_checksum=scoring.preprocessing_state_checksum,
    )
