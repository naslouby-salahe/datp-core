"""Independent centralized reconstruction scoring on pooled partitions."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
import polars as pl

from datp_core.centralized_reference.checkpointing import CentralizedCheckpointCandidate
from datp_core.centralized_reference.training import (
    CentralizedTrainingCoordinate,
    load_centralized_model_tensors,
)
from datp_core.domain.enums import ContractSubject, PartitionRole, ScoreFrameColumn, SerializationFormat
from datp_core.domain.errors import ArtifactIntegrityError, LeakageError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureCount,
    FeatureNameSequence,
    RoundNumber,
    RowCount,
    checksum_file,
    checksum_text,
)
from datp_core.learning.autoencoder import reconstruction_errors
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN, PopulationFrameColumn
from datp_core.protocols.anchor import (
    ANOMALY_POLARITY_FEATURE_PERTURBATION,
    FIXED_SCORE_ABSOLUTE_TOLERANCE,
    POLARITY_VERIFICATION_SAMPLE_LIMIT,
)
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.runtime.compute import resolve_cuda_device


class CentralizedScoreAssetName(StrEnum):
    CALIBRATION_SCORES = "calibration_scores.parquet"
    EVALUATION_SCORES = "evaluation_scores.parquet"
    SCORE_MANIFEST = "score_manifest.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class PooledScoreArtifact:
    coordinate: CentralizedTrainingCoordinate
    partition_role: PartitionRole
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    path: Path
    checksum: Checksum
    row_count: RowCount
    feature_count: FeatureCount
    serialization_format: SerializationFormat

    def __post_init__(self) -> None:
        if self.partition_role not in {PartitionRole.CALIBRATION, PartitionRole.EVALUATION}:
            raise ScientificContractError(
                "centralized score artifacts are only defined for calibration and evaluation",
                subject=self.partition_role,
            )
        if self.serialization_format is not SerializationFormat.PARQUET:
            raise ScientificContractError(
                "centralized scores must use Parquet serialization",
                subject=self.serialization_format,
            )


@dataclass(frozen=True, slots=True)
class CentralizedScoringResult:
    calibration_scores: PooledScoreArtifact
    evaluation_scores: PooledScoreArtifact
    higher_score_means_greater_anomaly: bool
    model_tensor_checksum: Checksum
    preprocessing_state_checksum: Checksum


@dataclass(frozen=True, slots=True)
class CentralizedScoringRequest:
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
    _assert_higher_score_is_anomaly_evidence(model, request)
    return CentralizedScoringResult(
        calibration_scores=calibration,
        evaluation_scores=evaluation,
        higher_score_means_greater_anomaly=True,
        model_tensor_checksum=request.checkpoint.tensor_checksum,
        preprocessing_state_checksum=request.preprocessing_state_checksum,
    )


def load_score_frame(artifact: PooledScoreArtifact) -> pl.DataFrame:
    if not artifact.path.is_file():
        raise ArtifactIntegrityError("score artifact is missing", subject=ContractSubject.ARTIFACT_PATH)
    frame = pl.read_parquet(artifact.path)
    if frame.height != artifact.row_count.value:
        raise ArtifactIntegrityError("score artifact row count mismatch", subject=ContractSubject.ARTIFACT_PATH)
    required = {
        ScoreFrameColumn.STABLE_ROW_ID.value,
        ScoreFrameColumn.OUTCOME_LABEL.value,
        ScoreFrameColumn.RECONSTRUCTION_ERROR.value,
    }
    if not required.issubset(set(frame.columns)):
        raise ArtifactIntegrityError("score artifact schema mismatch", subject=ContractSubject.ARTIFACT_PATH)
    return frame


def reject_threshold_identity_in_score_coordinate(threshold_identity: str | None) -> None:
    if threshold_identity is not None:
        raise ScientificContractError(
            "score coordinates must not include threshold identity",
            subject=ContractSubject.THRESHOLD_IDENTITY,
        )


def _validate_scoring_request(request: CentralizedScoringRequest) -> None:
    required_columns = (
        PopulationFrameColumn.STABLE_ROW_ID,
        PopulationFrameColumn.OUTCOME_LABEL,
    )
    for frame_name, frame in (
        (PartitionRole.CALIBRATION, request.calibration_features),
        (PartitionRole.EVALUATION, request.evaluation_features),
    ):
        for column in required_columns:
            if column.value not in frame.columns:
                raise ScientificContractError(
                    f"{frame_name.value} frame missing required column {column.value}",
                    subject=column,
                )
        missing = [name for name in request.feature_names if name not in frame.columns]
        if missing:
            raise ScientificContractError(
                f"{frame_name.value} frame missing declared features: {', '.join(missing)}",
                subject=ContractSubject.FEATURES,
            )


def _score_partition(
    *,
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    request: CentralizedScoringRequest,
    model,
    device,
    destination: Path,
) -> PooledScoreArtifact:
    matrix = frame.select(request.feature_names.as_list()).to_numpy().astype(np.float32, copy=False)
    row_ids = tuple(str(value) for value in frame.get_column(STABLE_ROW_ID_COLUMN).to_list())
    labels = tuple(str(value) for value in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
    if len(row_ids) != matrix.shape[0] or len(labels) != matrix.shape[0]:
        raise ScientificContractError("score partition rows must align", subject=partition_role)
    scores = reconstruction_errors(model, matrix, batch_size=request.batch_size, device=device)
    if scores.shape[0] != matrix.shape[0]:
        raise ScientificContractError("score count must equal partition row count", subject=partition_role)
    output = pl.DataFrame(
        {
            ScoreFrameColumn.STABLE_ROW_ID.value: list(row_ids),
            ScoreFrameColumn.OUTCOME_LABEL.value: list(labels),
            ScoreFrameColumn.RECONSTRUCTION_ERROR.value: scores.tolist(),
        }
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.write_parquet(destination)
    artifact = PooledScoreArtifact(
        coordinate=request.coordinate,
        partition_role=partition_role,
        checkpoint_round=request.checkpoint.round_number,
        checkpoint_checksum=request.checkpoint.tensor_checksum,
        path=destination,
        checksum=checksum_file(destination),
        row_count=RowCount(output.height),
        feature_count=FeatureCount(len(request.feature_names)),
        serialization_format=SerializationFormat.PARQUET,
    )
    _assert_reload_equality(output, artifact)
    return artifact


def _assert_higher_score_is_anomaly_evidence(model, request: CentralizedScoringRequest) -> None:
    """Verify MSE reconstruction error increases under larger feature perturbation."""
    device = resolve_cuda_device()
    sample = _polarity_sample_matrix(request.calibration_features, request.feature_names)
    if sample.shape[0] == 0:
        sample = _polarity_sample_matrix(request.evaluation_features, request.feature_names)
    if sample.shape[0] == 0:
        raise ScientificContractError(
            "cannot verify anomaly-score polarity without rows",
            subject=ContractSubject.SCORES,
        )
    baseline = reconstruction_errors(model, sample, batch_size=request.batch_size, device=device)
    perturbed = reconstruction_errors(
        model,
        sample + ANOMALY_POLARITY_FEATURE_PERTURBATION.value,
        batch_size=request.batch_size,
        device=device,
    )
    if not np.all(perturbed >= baseline - FIXED_SCORE_ABSOLUTE_TOLERANCE.value):
        raise ScientificContractError(
            "reconstruction error polarity failed: higher error must indicate greater anomaly evidence",
            subject=ContractSubject.RECONSTRUCTION_ERROR,
        )


def _polarity_sample_matrix(frame: pl.DataFrame, feature_names: FeatureNameSequence) -> np.ndarray:
    limit = min(POLARITY_VERIFICATION_SAMPLE_LIMIT.value, frame.height)
    if limit == 0:
        return np.asarray([], dtype=np.float32).reshape(0, len(feature_names))
    return frame.select(feature_names.as_list()).head(limit).to_numpy().astype(np.float32, copy=False)


def _assert_reload_equality(output: pl.DataFrame, artifact: PooledScoreArtifact) -> None:
    reloaded = pl.read_parquet(artifact.path)
    if output.shape != reloaded.shape:
        raise ArtifactIntegrityError("score reload shape mismatch", subject=ContractSubject.ARTIFACT_PATH)
    if not output.equals(reloaded):
        raise ArtifactIntegrityError("score reload equality failed", subject=ContractSubject.ARTIFACT_PATH)
    if checksum_file(artifact.path) != artifact.checksum:
        raise ArtifactIntegrityError("score checksum changed after write", subject=ContractSubject.ARTIFACT_PATH)


def score_artifact_set_checksum(result: CentralizedScoringResult) -> Checksum:
    return checksum_text(
        f"{result.calibration_scores.checksum.value}|{result.evaluation_scores.checksum.value}|"
        f"{result.model_tensor_checksum.value}"
    )


def reject_score_regeneration_per_threshold() -> None:
    raise LeakageError(
        "centralized scores are frozen detector outputs and must not be regenerated per threshold method",
        subject=ContractSubject.THRESHOLD_METHOD,
    )
