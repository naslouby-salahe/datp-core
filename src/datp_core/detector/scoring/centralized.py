from pathlib import Path

import numpy as np
import polars as pl

from datp_core.core.errors import ErrorMessage, ScientificContractError
from datp_core.core.identifiers import ContractSubject, PartitionRole, SerializationFormat
from datp_core.core.numeric import FeatureCount
from datp_core.detector.autoencoder import ReconstructionAutoencoder
from datp_core.detector.scoring.frames import (
    SCORE_FRAME_COLUMNS,
    SCORE_FRAME_DTYPES,
    model_from_terminal_state,
    score_and_persist_autoencoder_frame,
    validate_score_input_frame,
)
from datp_core.detector.scoring.models import (
    CentralizedScoreAssetName,
    CentralizedScoringRequest,
    CentralizedScoringResult,
    GenerateCentralizedScoresRequest,
    GenerateCentralizedScoresResult,
    PooledScoreArtifact,
)
from datp_core.runtime.compute import resolve_cuda_device


def generate_centralized_scores(request: GenerateCentralizedScoresRequest) -> GenerateCentralizedScoresResult:
    return GenerateCentralizedScoresResult(
        scoring=score_centralized_reference(
            CentralizedScoringRequest(
                coordinate=request.coordinate,
                training=request.training,
                autoencoder=request.autoencoder,
                feature_names=request.feature_names,
                calibration_features=request.calibration_features,
                evaluation_features=request.evaluation_features,
                batch_size=request.batch_size,
                output_directory=request.output_directory,
            )
        )
    )


def score_centralized_reference(request: CentralizedScoringRequest) -> CentralizedScoringResult:
    _validate_request(request)
    device = resolve_cuda_device()
    model = model_from_terminal_state(request.training.terminal_model_state, request.autoencoder, device)
    calibration = _score_partition(
        request,
        request.calibration_features,
        PartitionRole.CALIBRATION,
        model,
        request.output_directory / CentralizedScoreAssetName.CALIBRATION_SCORES,
    )
    evaluation = _score_partition(
        request,
        request.evaluation_features,
        PartitionRole.EVALUATION,
        model,
        request.output_directory / CentralizedScoreAssetName.EVALUATION_SCORES,
    )
    return CentralizedScoringResult(calibration_scores=calibration, evaluation_scores=evaluation)


def load_score_frame(artifact: PooledScoreArtifact) -> pl.DataFrame:
    if not artifact.path.is_file():
        raise ScientificContractError(ErrorMessage("score artifact is missing"), subject=ContractSubject.ARTIFACT_PATH)
    frame = pl.read_parquet(artifact.path)
    if frame.height != artifact.row_count.value:
        raise ScientificContractError(ErrorMessage("score artifact row count mismatch"), subject=ContractSubject.SCORES)
    if tuple(frame.columns) != SCORE_FRAME_COLUMNS:
        raise ScientificContractError(ErrorMessage("score artifact schema mismatch"), subject=ContractSubject.SCHEMA)
    if tuple(frame.schema[column] for column in SCORE_FRAME_COLUMNS) != SCORE_FRAME_DTYPES:
        raise ScientificContractError(ErrorMessage("score artifact dtype mismatch"), subject=ContractSubject.SCHEMA)
    return frame


def reject_non_finite_scores(scores: np.ndarray, *, message: ErrorMessage, subject: ContractSubject) -> None:
    if not np.isfinite(scores).all():
        raise ScientificContractError(message, subject=subject)


def _validate_request(request: CentralizedScoringRequest) -> None:
    if request.training.coordinate != request.coordinate:
        raise ScientificContractError(
            ErrorMessage("terminal training result coordinate mismatch during scoring"),
            subject=ContractSubject.COORDINATE,
        )
    validate_score_input_frame(request.calibration_features, PartitionRole.CALIBRATION, request.feature_names)
    validate_score_input_frame(request.evaluation_features, PartitionRole.EVALUATION, request.feature_names)


def _score_partition(
    request: CentralizedScoringRequest,
    frame: pl.DataFrame,
    role: PartitionRole,
    model: ReconstructionAutoencoder,
    destination: Path,
) -> PooledScoreArtifact:
    persisted = score_and_persist_autoencoder_frame(
        frame=frame,
        partition_role=role,
        feature_names=request.feature_names,
        model=model,
        batch_size=request.batch_size,
        device=resolve_cuda_device(),
        destination=destination,
    )
    return PooledScoreArtifact(
        coordinate=request.coordinate,
        partition_role=role,
        path=persisted.path,
        row_count=persisted.row_count,
        feature_count=FeatureCount(len(request.feature_names)),
        serialization_format=SerializationFormat.PARQUET,
    )
