"""Federated and centralized reconstruction-score publication."""

from dataclasses import dataclass, replace
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp_core.domain.enums import (
    ContractSubject,
    PartitionRole,
    PublicationStatus,
    ScoreFrameColumn,
    SerializationFormat,
    SplitProtocolId,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureCount,
    FeatureNameSequence,
    RoundNumber,
    RowCount,
    checksum_file,
)
from datp_core.learning.autoencoder import ReconstructionAutoencoder
from datp_core.learning.centralized.training import (
    CentralizedTrainingCoordinate,
    load_centralized_model_tensors,
)
from datp_core.learning.federated.models import CheckpointCandidate
from datp_core.pipeline.checkpoints.records import CentralizedCheckpointCandidate
from datp_core.pipeline.execution import PipelineStage
from datp_core.pipeline.publication.codec import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.pipeline.scoring.frame_contract import (
    validate_persisted_score_frame,
    validate_score_input_frame,
)
from datp_core.pipeline.scoring.service import (
    ClientScoringInput,
    FederatedScoreAssetName,
    FederatedScoreGenerationResult,
    ScoreGenerationRequest,
    federated_scoring_is_reusable,
    load_reused_federated_scores,
    rebase_federated_scores,
    score_and_persist_autoencoder_frame,
    write_federated_scores,
)
from datp_core.protocols.inference import ScoreArtifact
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.runtime.compute import resolve_cuda_device

IDENTITY_LENGTH_PREFIX_BYTES = 8


class CentralizedScoreAssetName(StrEnum):
    CALIBRATION_SCORES = "calibration_scores.parquet"
    EVALUATION_SCORES = "evaluation_scores.parquet"
    SCORE_MANIFEST = "score_manifest.json"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class PooledScoreArtifact(ScoreArtifact[CentralizedTrainingCoordinate]):
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
    coordinate: CentralizedTrainingCoordinate
    checkpoint: CentralizedCheckpointCandidate
    autoencoder: AutoencoderProtocol
    feature_names: FeatureNameSequence
    calibration_features: pl.DataFrame
    evaluation_features: pl.DataFrame
    batch_size: BatchSize
    output_directory: Path
    preprocessing_state_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class ScorePartitionBinding:
    partition_role: PartitionRole
    row_count: RowCount
    ordered_identity_checksum: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedScoringPublicationBinding:
    coordinate: CentralizedTrainingCoordinate
    checkpoint_round: RoundNumber
    checkpoint_checksum: Checksum
    preprocessing_state_checksum: Checksum
    split_manifest_checksum: Checksum
    feature_names: FeatureNameSequence
    batch_size: BatchSize
    calibration_input: ScorePartitionBinding
    evaluation_input: ScorePartitionBinding
    calibration_score_checksum: Checksum
    evaluation_score_checksum: Checksum


@dataclass(slots=True, eq=False, kw_only=True)
class GenerateFederatedScoresRequest:
    checkpoint: CheckpointCandidate
    scored_split_protocol: SplitProtocolId
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
    result: FederatedScoreGenerationResult


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


def score_centralized_reference(request: CentralizedScoringRequest) -> CentralizedScoringResult:
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
    published_request = replace(request, output_directory=directory)
    scoring = score_centralized_reference(published_request)
    (directory / CentralizedScoreAssetName.COMPLETE).write_text(
        score_artifact_set_checksum(published_request, scoring).value,
        encoding="utf-8",
    )
    return scoring


def centralized_scoring_is_reusable(request: CentralizedScoringRequest, directory: Path) -> bool:
    complete = directory / CentralizedScoreAssetName.COMPLETE
    calibration_path = directory / CentralizedScoreAssetName.CALIBRATION_SCORES
    evaluation_path = directory / CentralizedScoreAssetName.EVALUATION_SCORES
    if not (complete.is_file() and calibration_path.is_file() and evaluation_path.is_file()):
        return False
    try:
        _validate_scoring_request(request)
        calibration = _validated_reused_score_frame(
            request.calibration_features,
            calibration_path,
            PartitionRole.CALIBRATION,
        )
        evaluation = _validated_reused_score_frame(
            request.evaluation_features,
            evaluation_path,
            PartitionRole.EVALUATION,
        )
        scoring = _score_artifact_result(
            request,
            directory,
            calibration_row_count=RowCount(calibration.height),
            evaluation_row_count=RowCount(evaluation.height),
        )
        expected = score_artifact_set_checksum(request, scoring)
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except (ArtifactIntegrityError, OSError, ScientificContractError, UnicodeError, ValueError):
        return False


def load_reused_centralized_scoring(
    request: CentralizedScoringRequest,
    directory: Path,
) -> CentralizedScoringResult:
    calibration = _validated_reused_score_frame(
        request.calibration_features,
        directory / CentralizedScoreAssetName.CALIBRATION_SCORES,
        PartitionRole.CALIBRATION,
    )
    evaluation = _validated_reused_score_frame(
        request.evaluation_features,
        directory / CentralizedScoreAssetName.EVALUATION_SCORES,
        PartitionRole.EVALUATION,
    )
    return _score_artifact_result(
        request,
        directory,
        calibration_row_count=RowCount(calibration.height),
        evaluation_row_count=RowCount(evaluation.height),
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
    return CentralizedScoringResult(
        calibration_scores=_rebase_artifact(scoring.calibration_scores, calibration_path),
        evaluation_scores=_rebase_artifact(scoring.evaluation_scores, evaluation_path),
        model_tensor_checksum=scoring.model_tensor_checksum,
        preprocessing_state_checksum=scoring.preprocessing_state_checksum,
    )


def load_score_frame(artifact: PooledScoreArtifact) -> pl.DataFrame:
    return validate_persisted_score_frame(artifact.path, artifact.checksum, artifact.row_count)


def reject_non_finite_scores(
    scores: np.ndarray,
    *,
    message: str,
    subject: ContractSubject,
) -> None:
    if not np.isfinite(scores).all():
        raise ScientificContractError(message, subject=subject)


def score_artifact_set_checksum(
    request: CentralizedScoringRequest,
    result: CentralizedScoringResult,
) -> Checksum:
    return canonical_checksum(
        CentralizedScoringPublicationBinding(
            coordinate=request.coordinate,
            checkpoint_round=request.checkpoint.round_number,
            checkpoint_checksum=request.checkpoint.tensor_checksum,
            preprocessing_state_checksum=request.preprocessing_state_checksum,
            split_manifest_checksum=request.checkpoint.split_manifest_checksum,
            feature_names=request.feature_names,
            batch_size=request.batch_size,
            calibration_input=_score_partition_binding(request.calibration_features, PartitionRole.CALIBRATION),
            evaluation_input=_score_partition_binding(request.evaluation_features, PartitionRole.EVALUATION),
            calibration_score_checksum=result.calibration_scores.checksum,
            evaluation_score_checksum=result.evaluation_scores.checksum,
        )
    )


def _federated_request(request: GenerateFederatedScoresRequest, directory: Path) -> ScoreGenerationRequest:
    return ScoreGenerationRequest(
        checkpoint=request.checkpoint,
        scored_split_protocol=request.scored_split_protocol,
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
    validate_score_input_frame(request.calibration_features, PartitionRole.CALIBRATION, request.feature_names)
    validate_score_input_frame(request.evaluation_features, PartitionRole.EVALUATION, request.feature_names)


def _score_partition(
    *,
    frame: pl.DataFrame,
    partition_role: PartitionRole,
    request: CentralizedScoringRequest,
    model: ReconstructionAutoencoder,
    device: torch.device,
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


def _score_artifact_result(
    request: CentralizedScoringRequest,
    directory: Path,
    *,
    calibration_row_count: RowCount,
    evaluation_row_count: RowCount,
) -> CentralizedScoringResult:
    calibration, evaluation = _score_artifact_pair(
        request,
        directory,
        calibration_row_count=calibration_row_count,
        evaluation_row_count=evaluation_row_count,
    )
    return CentralizedScoringResult(
        calibration_scores=calibration,
        evaluation_scores=evaluation,
        model_tensor_checksum=request.checkpoint.tensor_checksum,
        preprocessing_state_checksum=request.preprocessing_state_checksum,
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


def _validated_reused_score_frame(
    source: pl.DataFrame,
    score_path: Path,
    partition_role: PartitionRole,
) -> pl.DataFrame:
    score_checksum = checksum_file(score_path)
    score = pl.read_parquet(score_path)
    validated = validate_persisted_score_frame(score_path, score_checksum, RowCount(score.height))
    if _score_partition_binding(validated, partition_role) != _score_partition_binding(source, partition_role):
        raise ArtifactIntegrityError(
            "persisted score row identities or labels do not match the current partition",
            subject=ContractSubject.ROWS,
        )
    return validated


def _score_partition_binding(frame: pl.DataFrame, partition_role: PartitionRole) -> ScorePartitionBinding:
    return ScorePartitionBinding(
        partition_role=partition_role,
        row_count=RowCount(frame.height),
        ordered_identity_checksum=_ordered_identity_checksum(frame),
    )


def _ordered_identity_checksum(frame: pl.DataFrame) -> Checksum:
    digest = sha256()
    columns = (ScoreFrameColumn.STABLE_ROW_ID.value, ScoreFrameColumn.OUTCOME_LABEL.value)
    for row_id, label in frame.select(columns).iter_rows():
        for value in (str(row_id), str(label)):
            encoded = value.encode("utf-8")
            digest.update(len(encoded).to_bytes(IDENTITY_LENGTH_PREFIX_BYTES, byteorder="big", signed=False))
            digest.update(encoded)
    return Checksum(digest.hexdigest())


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
