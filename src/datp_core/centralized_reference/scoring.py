"""Independent centralized reconstruction scoring on pooled partitions."""

from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path

import polars as pl

from datp_core.centralized_reference.checkpointing import CentralizedCheckpointCandidate
from datp_core.centralized_reference.training import (
    CentralizedTrainingCoordinate,
    load_centralized_model_tensors,
)
from datp_core.domain.enums import ContractSubject, PartitionRole, SerializationFormat
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
from datp_core.pipeline.scoring.frame_contract import validate_persisted_score_frame
from datp_core.pipeline.scoring.models import ScoreArtifact
from datp_core.pipeline.scoring.service import score_and_persist_autoencoder_frame
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.runtime.compute import resolve_cuda_device


class CentralizedScoreAssetName(StrEnum):
    CALIBRATION_SCORES = "calibration_scores.parquet"
    EVALUATION_SCORES = "evaluation_scores.parquet"
    SCORE_MANIFEST = "score_manifest.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class PooledScoreArtifact(ScoreArtifact[CentralizedTrainingCoordinate]):
    """One pooled score artifact for the independent centralized reference."""

    def __post_init__(self) -> None:
        ScoreArtifact.__post_init__(self)
        if self.partition_role not in {PartitionRole.CALIBRATION, PartitionRole.EVALUATION}:
            raise ScientificContractError(
                "centralized score artifacts are only defined for calibration and evaluation",
                subject=self.partition_role,
            )


@dataclass(frozen=True, slots=True)
class CentralizedScoringResult:
    calibration_scores: PooledScoreArtifact
    evaluation_scores: PooledScoreArtifact
    model_tensor_checksum: Checksum
    preprocessing_state_checksum: Checksum

    def __post_init__(self) -> None:
        if self.calibration_scores.partition_role is not PartitionRole.CALIBRATION:
            raise ScientificContractError(
                "centralized calibration score artifact has the wrong partition role",
                subject=ContractSubject.SCORES,
            )
        if self.evaluation_scores.partition_role is not PartitionRole.EVALUATION:
            raise ScientificContractError(
                "centralized evaluation score artifact has the wrong partition role",
                subject=ContractSubject.SCORES,
            )
        if self.calibration_scores.coordinate != self.evaluation_scores.coordinate:
            raise ScientificContractError(
                "centralized score artifacts must share one training coordinate",
                subject=ContractSubject.COORDINATE,
            )
        if self.calibration_scores.checkpoint_checksum != self.model_tensor_checksum:
            raise ScientificContractError(
                "centralized calibration scores must reference the selected model checksum",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )
        if self.evaluation_scores.checkpoint_checksum != self.model_tensor_checksum:
            raise ScientificContractError(
                "centralized evaluation scores must reference the selected model checksum",
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )


@dataclass(frozen=True, slots=True, eq=False)
class CentralizedScoringRequest:
    """Identity-based scoring command containing mutable Polars frames."""

    coordinate: CentralizedTrainingCoordinate
    checkpoint: CentralizedCheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_checksum: Checksum


def score_centralized_reference(request: CentralizedScoringRequest) -> CentralizedScoringResult:
    """Generate deterministic pooled reconstruction scores for calibration and evaluation."""
    _validate_scoring_request(request)
    device = resolve_cuda_device()
    model = load_centralized_model_tensors(request.checkpoint.tensor_path, request.autoencoder, device)
    request.output_directory.mkdir(parents=True, exist_ok=True)
    calibration = _score_partition(
        frame=request.calibration_features,
        partition_role=PartitionRole.CALIBRATION,
        request=request,
        model=model,
        device=device,
        destination=request.output_directory / CentralizedScoreAssetName.CALIBRATION_SCORES,
    )
    evaluation = _score_partition(
        frame=request.evaluation_features,
        partition_role=PartitionRole.EVALUATION,
        request=request,
        model=model,
        device=device,
        destination=request.output_directory / CentralizedScoreAssetName.EVALUATION_SCORES,
    )
    return CentralizedScoringResult(
        calibration_scores=calibration,
        evaluation_scores=evaluation,
        model_tensor_checksum=request.checkpoint.tensor_checksum,
        preprocessing_state_checksum=request.preprocessing_state_checksum,
    )


def write_centralized_scoring(
    request: CentralizedScoringRequest,
    directory: Path,
) -> CentralizedScoringResult:
    """Write a complete centralized score publication into a caller-owned directory."""
    scoring = score_centralized_reference(replace(request, output_directory=directory))
    (directory / CentralizedScoreAssetName.COMPLETE).write_text(
        score_artifact_set_checksum(scoring).value,
        encoding="utf-8",
    )
    return scoring


def centralized_scoring_is_reusable(
    request: CentralizedScoringRequest,
    directory: Path,
) -> bool:
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


def load_reused_centralized_scoring(
    request: CentralizedScoringRequest,
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


def rebase_centralized_scoring(
    scoring: CentralizedScoringResult,
    directory: Path,
) -> CentralizedScoringResult:
    calibration_path = directory / CentralizedScoreAssetName.CALIBRATION_SCORES
    evaluation_path = directory / CentralizedScoreAssetName.EVALUATION_SCORES
    if not calibration_path.is_file() or not evaluation_path.is_file():
        raise ArtifactIntegrityError(
            "published score partitions missing after atomic replace",
            subject=ContractSubject.SCORES,
        )
    calibration = _rebase_artifact(scoring.calibration_scores, calibration_path)
    evaluation = _rebase_artifact(scoring.evaluation_scores, evaluation_path)
    return CentralizedScoringResult(
        calibration_scores=calibration,
        evaluation_scores=evaluation,
        model_tensor_checksum=scoring.model_tensor_checksum,
        preprocessing_state_checksum=scoring.preprocessing_state_checksum,
    )


def load_score_frame(artifact: PooledScoreArtifact) -> pl.DataFrame:
    return validate_persisted_score_frame(artifact.path, artifact.checksum, artifact.row_count)


def _validate_scoring_request(request: CentralizedScoringRequest) -> None:
    if request.checkpoint.coordinate != request.coordinate:
        raise ScientificContractError(
            "checkpoint coordinate mismatch during scoring",
            subject=ContractSubject.COORDINATE,
        )
    if request.checkpoint.preprocessing_state_checksum != request.preprocessing_state_checksum:
        raise ScientificContractError(
            "checkpoint preprocessing checksum mismatch during scoring",
            subject=ContractSubject.PREPROCESSING,
        )


def _score_partition(
    *,
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    request: CentralizedScoringRequest,
    model: object,
    device: object,
    destination: Path,
) -> PooledScoreArtifact:
    persisted = score_and_persist_autoencoder_frame(
        frame=frame,
        partition_role=partition_role,
        feature_names=request.feature_names,
        model=model,
        batch_size=request.batch_size,
        device=device,
        destination=destination,
    )
    return PooledScoreArtifact(
        coordinate=request.coordinate,
        partition_role=partition_role,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        path=persisted.path,
        checksum=persisted.checksum,
        row_count=persisted.row_count,
        feature_count=persisted.feature_count,
        serialization_format=SerializationFormat.PARQUET,
    )


def _score_artifact_pair(
    request: CentralizedScoringRequest,
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


def _rebase_artifact(artifact: PooledScoreArtifact, path: Path) -> PooledScoreArtifact:
    return PooledScoreArtifact(
        coordinate=artifact.coordinate,
        partition_role=artifact.partition_role,
        checkpoint_round=artifact.checkpoint_round,
        checkpoint_checksum=artifact.checkpoint_checksum,
        path=path,
        checksum=checksum_file(path),
        row_count=artifact.row_count,
        feature_count=artifact.feature_count,
        serialization_format=artifact.serialization_format,
    )


def score_artifact_set_checksum(result: CentralizedScoringResult) -> Checksum:
    return checksum_text(
        f"{result.calibration_scores.checksum.value}|{result.evaluation_scores.checksum.value}|"
        f"{result.model_tensor_checksum.value}"
    )
