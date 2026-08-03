"""Stage: score pooled partitions with the selected centralized checkpoint."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.store import AtomicPublication, publish_atomically
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
from datp_core.protocols.models import AutoencoderProtocol


@dataclass(frozen=True, slots=True)
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
    stage: StageOperationId
    publication_status: PublicationStatus
    scoring: CentralizedScoringResult
    complete_digest: Checksum


def score_centralized_reference_stage(
    request: ScoreCentralizedReferenceRequest,
) -> ScoreCentralizedReferenceResult:
    if request.checkpoint.coordinate != request.coordinate:
        raise ScientificContractError("score stage checkpoint coordinate mismatch", subject=ContractSubject.COORDINATE)

    holder: dict[str, CentralizedScoringResult] = {}

    def write(temporary: Path) -> None:
        scoring = score_centralized_reference(
            CentralizedScoringRequest(
                coordinate=request.coordinate,
                checkpoint=request.checkpoint,
                autoencoder=request.autoencoder,
                feature_names=request.feature_names,
                calibration_features=request.calibration_features,
                evaluation_features=request.evaluation_features,
                batch_size=request.batch_size,
                output_directory=temporary,
                preprocessing_state_checksum=request.preprocessing_state_checksum,
            )
        )
        digest = score_artifact_set_checksum(scoring)
        (temporary / CentralizedScoreAssetName.COMPLETE).write_text(digest.value, encoding="utf-8")
        holder["scoring"] = scoring

    reused = publish_atomically(
        AtomicPublication(
            target=request.output_directory,
            overwrite=request.overwrite,
            is_reusable=lambda directory: _is_reusable(directory, request),
            write=write,
            remove_target=lambda directory: rmtree(directory),
        )
    )
    if reused:
        scoring = _load_reused_scores(request)
        status = PublicationStatus.REUSED
    else:
        scoring = holder["scoring"]
        scoring = _rebase_scoring(scoring, request)
        status = PublicationStatus.PUBLISHED
    return ScoreCentralizedReferenceResult(
        stage=StageOperationId.SCORE_CENTRALIZED_REFERENCE,
        publication_status=status,
        scoring=scoring,
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
    *,
    calibration_row_count: RowCount,
    evaluation_row_count: RowCount,
) -> tuple[PooledScoreArtifact, PooledScoreArtifact]:
    calibration_path = request.output_directory / CentralizedScoreAssetName.CALIBRATION_SCORES
    evaluation_path = request.output_directory / CentralizedScoreAssetName.EVALUATION_SCORES
    calibration = PooledScoreArtifact(
        coordinate=request.coordinate,
        partition_role=PartitionRole.CALIBRATION,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        path=calibration_path,
        checksum=checksum_file(calibration_path),
        row_count=calibration_row_count,
        feature_count=FeatureCount(len(request.feature_names)),
        serialization_format=SerializationFormat.PARQUET,
    )
    evaluation = PooledScoreArtifact(
        coordinate=request.coordinate,
        partition_role=PartitionRole.EVALUATION,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        path=evaluation_path,
        checksum=checksum_file(evaluation_path),
        row_count=evaluation_row_count,
        feature_count=FeatureCount(len(request.feature_names)),
        serialization_format=SerializationFormat.PARQUET,
    )
    return calibration, evaluation


def _load_reused_scores(request: ScoreCentralizedReferenceRequest) -> CentralizedScoringResult:
    calibration_frame = pl.read_parquet(request.output_directory / CentralizedScoreAssetName.CALIBRATION_SCORES)
    evaluation_frame = pl.read_parquet(request.output_directory / CentralizedScoreAssetName.EVALUATION_SCORES)
    calibration, evaluation = _score_artifact_pair(
        request,
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
    request: ScoreCentralizedReferenceRequest,
) -> CentralizedScoringResult:
    calibration_path = request.output_directory / CentralizedScoreAssetName.CALIBRATION_SCORES
    evaluation_path = request.output_directory / CentralizedScoreAssetName.EVALUATION_SCORES
    if not calibration_path.is_file() or not evaluation_path.is_file():
        raise ArtifactIntegrityError(
            "published score partitions missing after atomic replace", subject=ContractSubject.SCORES
        )
    calibration, evaluation = _score_artifact_pair(
        request,
        calibration_row_count=scoring.calibration_scores.row_count,
        evaluation_row_count=scoring.evaluation_scores.row_count,
    )
    return CentralizedScoringResult(
        calibration_scores=calibration,
        evaluation_scores=evaluation,
        model_tensor_checksum=scoring.model_tensor_checksum,
        preprocessing_state_checksum=scoring.preprocessing_state_checksum,
    )
