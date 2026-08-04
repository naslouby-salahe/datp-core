"""Stage: train the independent centralized autoencoder reference."""

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import polars as pl
import torch

from datp_core.centralized_reference.checkpointing import (
    CentralizedCheckpointCandidate,
    candidate_tensor_name,
    retain_centralized_checkpoint_candidates,
)
from datp_core.centralized_reference.training import (
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
from datp_core.domain.enums import (
    CentralizedModelId,
    CheckpointStatus,
    ContractSubject,
    PublicationStatus,
    StageOperationId,
    TrainingHistoryColumn,
)
from datp_core.domain.errors import ArtifactIntegrityError, ScientificContractError
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    CudaDeviceName,
    FeatureCount,
    FeatureNameSequence,
    LearningRate,
    MetricValue,
    RoundNumber,
    RowCount,
    Seed,
    WeightDecay,
    checksum_file,
    checksum_text,
)
from datp_core.pipeline.publication.codec import ArtifactPublication, publish_artifact
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.protocols.models import (
    AutoencoderProtocol,
    CentralizedTrainingProtocol,
    CheckpointProtocol,
)
from datp_core.runtime.compute import resolve_cuda_device


@dataclass(slots=True, eq=False)
class TrainCentralizedReferenceRequest:
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


@dataclass(frozen=True, slots=True)
class _CentralizedTrainingArtifacts:
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]


@dataclass(frozen=True, slots=True)
class TrainCentralizedReferenceResult:
    stage: ClassVar[StageOperationId] = StageOperationId.TRAIN_CENTRALIZED_REFERENCE
    publication_status: PublicationStatus
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    complete_digest: Checksum


@dataclass(frozen=True, slots=True, kw_only=True)
class _CentralizedTrainingCodec:
    training_protocol: CentralizedTrainingProtocol
    learning_rate: LearningRate
    batch_size: BatchSize
    weight_decay: WeightDecay

    def write(
        self,
        request: TrainCentralizedReferenceRequest,
        directory: Path,
    ) -> _CentralizedTrainingArtifacts:
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
                training_protocol=self.training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                learning_rate=self.learning_rate,
                batch_size=self.batch_size,
                benign_label=PopulationOutcomeLabel.BENIGN,
            )
        )
        training = execution.result
        candidates = retain_centralized_checkpoint_candidates(execution, request.autoencoder)
        training_history_frame(training).write_parquet(directory / CentralizedArtifactName.TRAINING_HISTORY)
        (directory / CentralizedArtifactName.COMPLETE).write_text(
            _complete_digest(training).value,
            encoding="utf-8",
        )
        return _CentralizedTrainingArtifacts(training, candidates)

    def validate(self, request: TrainCentralizedReferenceRequest, directory: Path) -> bool:
        return _is_reusable(directory, request, self.batch_size)

    def load(
        self,
        request: TrainCentralizedReferenceRequest,
        directory: Path,
    ) -> _CentralizedTrainingArtifacts:
        training, candidates = _load_reused_training(
            request,
            directory,
            self.training_protocol,
            self.learning_rate,
            self.batch_size,
            self.weight_decay,
        )
        return _CentralizedTrainingArtifacts(training, candidates)

    def rebase(
        self,
        result: _CentralizedTrainingArtifacts,
        directory: Path,
    ) -> _CentralizedTrainingArtifacts:
        return _CentralizedTrainingArtifacts(
            _rebase_training_paths(result.training, directory),
            _rebase_candidates(result.candidates, directory),
        )


def train_centralized_reference_stage(
    request: TrainCentralizedReferenceRequest,
) -> TrainCentralizedReferenceResult:
    require_no_hidden_scientific_defaults()
    training_protocol, _declared_autoencoder, learning_rate, batch_size, weight_decay = (
        declared_centralized_training_values()
    )
    _validate_request(request)
    publication = publish_artifact(
        ArtifactPublication(
            target=request.output_directory,
            request=request,
            codec=_CentralizedTrainingCodec(
                training_protocol=training_protocol,
                learning_rate=learning_rate,
                batch_size=batch_size,
                weight_decay=weight_decay,
            ),
            overwrite=request.overwrite,
            complete_marker=CentralizedArtifactName.COMPLETE,
        )
    )
    artifacts = publication.value
    return TrainCentralizedReferenceResult(
        publication_status=publication.status,
        training=artifacts.training,
        candidates=artifacts.candidates,
        complete_digest=checksum_file(request.output_directory / CentralizedArtifactName.COMPLETE),
    )


def _validate_request(request: TrainCentralizedReferenceRequest) -> None:
    if request.autoencoder.widths[0] != len(request.feature_names):
        raise ScientificContractError(
            "autoencoder input width must match the feature schema",
            subject=ContractSubject.AUTOENCODER,
        )
    if request.coordinate.model is not CentralizedModelId.CENTRALIZED_AUTOENCODER:
        raise ScientificContractError(
            "train stage requires CENTRALIZED_AUTOENCODER",
            subject=request.coordinate.model,
        )


def _complete_digest(training: CentralizedTrainingResult) -> Checksum:
    return checksum_text(
        f"{training.model_tensor_checksum.value}|{training.final_epoch.value}|{training.batch_size_used.value}"
    )


def _is_reusable(
    directory: Path,
    request: TrainCentralizedReferenceRequest,
    batch_size: BatchSize,
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
        expected = checksum_text(
            f"{checksum_file(model).value}|{request.checkpoint_protocol.maximum_round.value}|{batch_size.value}"
        )
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except (OSError, ValueError):
        return False


def _load_reused_training(
    request: TrainCentralizedReferenceRequest,
    directory: Path,
    training_protocol: CentralizedTrainingProtocol,
    learning_rate: LearningRate,
    batch_size: BatchSize,
    weight_decay: WeightDecay,
) -> tuple[CentralizedTrainingResult, tuple[CentralizedCheckpointCandidate, ...]]:
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
        autoencoder_widths=tuple(request.autoencoder.widths),
        optimizer=CentralizedOptimizerSummary(
            identity=training_protocol.optimizer.identity,
            learning_rate=learning_rate,
            weight_decay=weight_decay,
            batch_size=batch_size,
        ),
        checkpoint_protocol=request.checkpoint_protocol,
        training_protocol=training_protocol,
        training_seed=request.training_seed,
        train_row_count=RowCount(request.training_features.height),
        feature_count=FeatureCount(len(request.feature_names)),
        epoch_losses=epoch_losses,
        model_directory=directory,
        model_tensor_path=model_path,
        model_tensor_checksum=checksum_file(model_path),
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=CudaDeviceName(torch.cuda.get_device_name(resolve_cuda_device())),
        batch_size_used=batch_size,
        final_epoch=request.checkpoint_protocol.maximum_round,
    )
    return training, candidates


def _load_reused_candidate(
    request: TrainCentralizedReferenceRequest,
    directory: Path,
    candidate_round: RoundNumber,
    epoch_losses: tuple[CentralizedEpochLoss, ...],
) -> CentralizedCheckpointCandidate:
    path = directory / candidate_tensor_name(candidate_round)
    if not path.is_file():
        raise ArtifactIntegrityError(
            "reused checkpoint candidate missing",
            subject=ContractSubject.ARTIFACT_PATH,
        )
    matching_losses = tuple(
        item.mean_training_loss for item in epoch_losses if item.epoch == candidate_round
    )
    if len(matching_losses) != 1:
        raise ArtifactIntegrityError(
            "reused checkpoint candidate requires exactly one matching training loss",
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return CentralizedCheckpointCandidate(
        coordinate=request.coordinate,
        round_number=candidate_round,
        tensor_path=path,
        tensor_checksum=checksum_file(path),
        mean_training_loss=matching_losses[0],
        status=CheckpointStatus.CANDIDATE,
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        training_seed=request.training_seed,
        autoencoder_widths=tuple(request.autoencoder.widths),
    )


def _rebase_training_paths(training: CentralizedTrainingResult, directory: Path) -> CentralizedTrainingResult:
    model_path = directory / CentralizedArtifactName.MODEL_TENSORS
    return CentralizedTrainingResult(
        coordinate=training.coordinate,
        autoencoder_widths=training.autoencoder_widths,
        optimizer=training.optimizer,
        checkpoint_protocol=training.checkpoint_protocol,
        training_protocol=training.training_protocol,
        training_seed=training.training_seed,
        train_row_count=training.train_row_count,
        feature_count=training.feature_count,
        epoch_losses=training.epoch_losses,
        model_directory=directory,
        model_tensor_path=model_path,
        model_tensor_checksum=checksum_file(model_path),
        preprocessing_state_checksum=training.preprocessing_state_checksum,
        split_manifest_checksum=training.split_manifest_checksum,
        device_name=training.device_name,
        batch_size_used=training.batch_size_used,
        final_epoch=training.final_epoch,
    )


def _rebase_candidates(
    candidates: tuple[CentralizedCheckpointCandidate, ...],
    directory: Path,
) -> tuple[CentralizedCheckpointCandidate, ...]:
    return tuple(_rebase_candidate(candidate, directory) for candidate in candidates)


def _rebase_candidate(
    candidate: CentralizedCheckpointCandidate,
    directory: Path,
) -> CentralizedCheckpointCandidate:
    tensor_path = directory / candidate_tensor_name(candidate.round_number)
    return CentralizedCheckpointCandidate(
        coordinate=candidate.coordinate,
        round_number=candidate.round_number,
        tensor_path=tensor_path,
        tensor_checksum=checksum_file(tensor_path),
        mean_training_loss=candidate.mean_training_loss,
        status=candidate.status,
        preprocessing_state_checksum=candidate.preprocessing_state_checksum,
        split_manifest_checksum=candidate.split_manifest_checksum,
        training_seed=candidate.training_seed,
        autoencoder_widths=candidate.autoencoder_widths,
    )
