"""Independent centralized reconstruction scoring on pooled partitions."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import polars as pl
import torch

from datp_core.artifacts.score_frames import (
    extract_score_arrays,
    score_frame,
    validate_persisted_score_frame,
    validate_score_input_frame,
)
from datp_core.artifacts.score_models import ScoreArtifact
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
from datp_core.learning.autoencoder import ReconstructionAutoencoder, reconstruction_errors
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
    validate_score_input_frame(
        request.calibration_features,
        PartitionRole.CALIBRATION,
        request.feature_names,
    )
    validate_score_input_frame(
        request.evaluation_features,
        PartitionRole.EVALUATION,
        request.feature_names,
    )


def _score_partition(
    *,
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    request: CentralizedScoringRequest,
    model: ReconstructionAutoencoder,
    device: torch.device,
    destination: Path,
) -> PooledScoreArtifact:
    matrix, labels, row_ids = extract_score_arrays(frame, request.feature_names)
    scores = reconstruction_errors(model, matrix, batch_size=request.batch_size, device=device)
    if scores.shape[0] != matrix.shape[0]:
        raise ScientificContractError("score count must equal partition row count", subject=partition_role)
    output = score_frame(row_ids, labels, scores)
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


def _assert_reload_equality(output: pl.DataFrame, artifact: PooledScoreArtifact) -> None:
    reloaded = validate_persisted_score_frame(artifact.path, artifact.checksum, artifact.row_count)
    if output.shape != reloaded.shape:
        raise ArtifactIntegrityError("score reload shape mismatch", subject=ContractSubject.ARTIFACT_PATH)
    if not output.equals(reloaded):
        raise ArtifactIntegrityError("score reload equality failed", subject=ContractSubject.ARTIFACT_PATH)


def score_artifact_set_checksum(result: CentralizedScoringResult) -> Checksum:
    return checksum_text(
        f"{result.calibration_scores.checksum.value}|{result.evaluation_scores.checksum.value}|"
        f"{result.model_tensor_checksum.value}"
    )
