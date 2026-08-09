"""Centralized detector training publication."""

from dataclasses import dataclass, replace
from pathlib import Path

import polars as pl
import torch

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.repositories.publication import ArtifactPublication, FunctionalArtifactCodec, publish_artifact
from datp_core.artifacts.serializers.json import canonical_checksum
from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import (
    CentralizedModelId,
    CheckpointStatus,
    ContractSubject,
    CudaDeviceName,
    FeatureNameSequence,
    OptimizerId,
    PublicationStatus,
    TrainingHistoryColumn,
)
from datp_core.core.numeric import (
    BatchSize,
    FeatureCount,
    LearningRate,
    MetricValue,
    RoundNumber,
    RowCount,
    Seed,
    WeightDecay,
)
from datp_core.data.populations.contracts import PopulationOutcomeLabel
from datp_core.data.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.checkpoints.models import CentralizedCheckpointCandidate
from datp_core.detector.checkpoints.service import candidate_tensor_name, retain_centralized_checkpoint_candidates
from datp_core.detector.training.centralized import (
    CentralizedArtifactName,
    CentralizedEpochLoss,
    CentralizedOptimizerSummary,
    CentralizedTrainingCoordinate,
    CentralizedTrainingRequest,
    CentralizedTrainingResult,
    declared_centralized_training_values,
    require_no_hidden_scientific_defaults,
    train_centralized_autoencoder,
    training_history_frame,
)
from datp_core.detector.training.contracts import AutoencoderProtocol, CentralizedTrainingProtocol
from datp_core.runtime.compute import resolve_cuda_device


@dataclass(slots=True, eq=False, kw_only=True)
class TrainCentralizedDetectorRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    split_manifest_checksum: Checksum
    output_directory: Path
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    checkpoint_protocol: CheckpointProtocol
    overwrite: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class TrainCentralizedDetectorResult:
    publication_status: PublicationStatus
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    complete_digest: Checksum


@dataclass(slots=True, eq=False, kw_only=True)
class CentralizedTrainingPublicationRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    split_manifest_checksum: Checksum
    output_directory: Path
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    checkpoint_protocol: CheckpointProtocol
    training_protocol: CentralizedTrainingProtocol
    learning_rate: LearningRate
    batch_size: BatchSize
    weight_decay: WeightDecay


@dataclass(frozen=True, slots=True)
class CentralizedTrainingArtifacts:
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CentralizedTrainingPublicationBinding:
    """Immutable identity of one published centralized training artifact set."""

    coordinate: CentralizedTrainingCoordinate
    model_tensor_checksum: Checksum
    final_epoch: RoundNumber
    batch_size: BatchSize
    preprocessing_state_checksum: Checksum
    split_manifest_checksum: Checksum
    feature_count: FeatureCount
    autoencoder_widths: tuple[FeatureCount, ...]
    train_row_count: RowCount
    optimizer_identity: OptimizerId
    learning_rate: LearningRate
    weight_decay: WeightDecay
    checkpoint_rounds: tuple[RoundNumber, ...]


def _centralized_training_binding(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
) -> CentralizedTrainingPublicationBinding:
    return CentralizedTrainingPublicationBinding(
        coordinate=request.coordinate,
        model_tensor_checksum=Checksum.from_file(directory / CentralizedArtifactName.MODEL_TENSORS),
        final_epoch=request.checkpoint_protocol.maximum_round,
        batch_size=request.batch_size,
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        feature_count=FeatureCount(len(request.feature_names)),
        autoencoder_widths=tuple(request.autoencoder.widths),
        train_row_count=RowCount(request.training_features.height),
        optimizer_identity=request.training_protocol.optimizer.identity,
        learning_rate=request.learning_rate,
        weight_decay=request.weight_decay,
        checkpoint_rounds=tuple(request.checkpoint_protocol.candidates),
    )


def train_centralized_detector(request: TrainCentralizedDetectorRequest) -> TrainCentralizedDetectorResult:
    require_no_hidden_scientific_defaults()
    training_protocol, _, learning_rate, batch_size, weight_decay = declared_centralized_training_values()
    publication_request = CentralizedTrainingPublicationRequest(
        coordinate=request.coordinate,
        training_features=request.training_features,
        feature_names=request.feature_names,
        preprocessing_state=request.preprocessing_state,
        split_manifest_checksum=request.split_manifest_checksum,
        output_directory=request.output_directory,
        training_seed=request.training_seed,
        autoencoder=request.autoencoder,
        checkpoint_protocol=request.checkpoint_protocol,
        training_protocol=training_protocol,
        learning_rate=learning_rate,
        batch_size=batch_size,
        weight_decay=weight_decay,
    )
    validate_centralized_training_request(publication_request)
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=publication_request,
            codec=FunctionalArtifactCodec(
                writer=write_centralized_training,
                validator=centralized_training_is_reusable,
                loader=load_reused_centralized_training,
                rebaser=rebase_centralized_training,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedArtifactName.COMPLETE,
        )
    )
    artifacts: CentralizedTrainingArtifacts = publication.value
    return TrainCentralizedDetectorResult(
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
        complete_digest=publication.complete_digest,
    )


def validate_centralized_training_request(request: CentralizedTrainingPublicationRequest) -> None:
    if request.autoencoder.widths[0].value != len(request.feature_names):
        raise ScientificContractError(
            ErrorMessage("autoencoder input width must match the feature schema"),
            subject=ContractSubject.AUTOENCODER,
        )
    if request.coordinate.model is not CentralizedModelId.CENTRALIZED_AUTOENCODER:
        raise ScientificContractError(
            ErrorMessage("train stage requires CENTRALIZED_AUTOENCODER"),
            subject=request.coordinate.model,
        )


def write_centralized_training(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
) -> CentralizedTrainingArtifacts:
    execution = train_centralized_autoencoder(
        CentralizedTrainingRequest(
            coordinate=request.coordinate,
            training_features=request.training_features,
            feature_names=request.feature_names,
            preprocessing_state=request.preprocessing_state,
            split_manifest_checksum=request.split_manifest_checksum,
            output_directory=directory,
            training_seed=request.training_seed,
            autoencoder=request.autoencoder,
            training_protocol=request.training_protocol,
            checkpoint_protocol=request.checkpoint_protocol,
            learning_rate=request.learning_rate,
            batch_size=request.batch_size,
            benign_label=PopulationOutcomeLabel.BENIGN,
        )
    )
    training = execution.result
    candidates = retain_centralized_checkpoint_candidates(execution, request.autoencoder)
    training_history_frame(training).write_parquet(directory / CentralizedArtifactName.TRAINING_HISTORY)
    (directory / CentralizedArtifactName.COMPLETE).write_text(
        canonical_checksum(_centralized_training_binding(request, directory)).value,
        encoding="utf-8",
    )
    return CentralizedTrainingArtifacts(training, candidates)


def centralized_training_is_reusable(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
) -> bool:
    complete = directory / CentralizedArtifactName.COMPLETE
    model = directory / CentralizedArtifactName.MODEL_TENSORS
    history = directory / CentralizedArtifactName.TRAINING_HISTORY
    if not (complete.is_file() and model.is_file() and history.is_file()):
        return False
    if any(
        not (directory / candidate_tensor_name(candidate)).is_file()
        for candidate in request.checkpoint_protocol.candidates
    ):
        return False
    try:
        expected = canonical_checksum(_centralized_training_binding(request, directory))
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except (OSError, ValueError):
        return False


def load_reused_centralized_training(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
) -> CentralizedTrainingArtifacts:
    history = pl.read_parquet(directory / CentralizedArtifactName.TRAINING_HISTORY)
    epoch_losses = tuple(
        CentralizedEpochLoss(
            epoch=RoundNumber(int(epoch)),
            mean_training_loss=MetricValue(float(loss)),
        )
        for epoch, loss in history.select(
            (
                TrainingHistoryColumn.EPOCH.value,
                TrainingHistoryColumn.MEAN_TRAINING_LOSS.value,
            )
        ).iter_rows()
    )
    candidates = tuple(
        _load_reused_candidate(request, directory, candidate_round, epoch_losses)
        for candidate_round in request.checkpoint_protocol.candidates
    )
    model_path = directory / CentralizedArtifactName.MODEL_TENSORS
    training = CentralizedTrainingResult(
        coordinate=request.coordinate,
        autoencoder_widths=request.autoencoder.widths,
        optimizer=CentralizedOptimizerSummary(
            identity=request.training_protocol.optimizer.identity,
            learning_rate=request.learning_rate,
            weight_decay=request.weight_decay,
            batch_size=request.batch_size,
        ),
        checkpoint_protocol=request.checkpoint_protocol,
        training_protocol=request.training_protocol,
        training_seed=request.training_seed,
        train_row_count=RowCount(request.training_features.height),
        feature_count=FeatureCount(len(request.feature_names)),
        epoch_losses=epoch_losses,
        model_directory=directory,
        model_tensor_path=model_path,
        model_tensor_checksum=Checksum.from_file(model_path),
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=CudaDeviceName(torch.cuda.get_device_name(resolve_cuda_device())),
        batch_size_used=request.batch_size,
        final_epoch=request.checkpoint_protocol.maximum_round,
    )
    return CentralizedTrainingArtifacts(training, candidates)


def rebase_centralized_training(
    result: CentralizedTrainingArtifacts,
    directory: Path,
) -> CentralizedTrainingArtifacts:
    model_path = directory / CentralizedArtifactName.MODEL_TENSORS
    training = replace(
        result.training,
        model_directory=directory,
        model_tensor_path=model_path,
        model_tensor_checksum=Checksum.from_file(model_path),
    )
    candidates = tuple(
        replace(
            candidate,
            tensor_path=directory / candidate_tensor_name(candidate.round_number),
            tensor_checksum=Checksum.from_file(directory / candidate_tensor_name(candidate.round_number)),
        )
        for candidate in result.candidates
    )
    return CentralizedTrainingArtifacts(training, candidates)


def _load_reused_candidate(
    request: CentralizedTrainingPublicationRequest,
    directory: Path,
    candidate_round: RoundNumber,
    epoch_losses: tuple[CentralizedEpochLoss, ...],
) -> CentralizedCheckpointCandidate:
    path = directory / candidate_tensor_name(candidate_round)
    if not path.is_file():
        raise ArtifactIntegrityError(
            ErrorMessage("reused checkpoint candidate missing"),
            subject=ContractSubject.ARTIFACT_PATH,
        )
    matching_losses = tuple(item.mean_training_loss for item in epoch_losses if item.epoch == candidate_round)
    if len(matching_losses) != 1:
        raise ArtifactIntegrityError(
            ErrorMessage("reused checkpoint candidate requires exactly one matching training loss"),
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return CentralizedCheckpointCandidate(
        coordinate=request.coordinate,
        round_number=candidate_round,
        tensor_path=path,
        tensor_checksum=Checksum.from_file(path),
        mean_training_loss=matching_losses[0],
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        training_seed=request.training_seed,
        autoencoder_widths=request.autoencoder.widths,
    )
