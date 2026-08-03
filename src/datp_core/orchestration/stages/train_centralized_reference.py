"""Stage: train the independent centralized autoencoder reference."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree

import polars as pl

from datp_core.artifacts.store import AtomicPublication, publish_atomically
from datp_core.centralized_reference.checkpointing import (
    CentralizedCheckpointCandidate,
    candidate_tensor_name,
    retain_centralized_checkpoint_candidates,
)
from datp_core.centralized_reference.training import (
    CentralizedArtifactName,
    CentralizedEpochLoss,
    CentralizedModelSnapshot,
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
    Checksum,
    FeatureCount,
    FeatureNameSequence,
    MetricValue,
    RoundNumber,
    RowCount,
    Seed,
    WeightDecay,
    checksum_file,
    checksum_text,
)
from datp_core.populations.models import PopulationOutcomeLabel
from datp_core.preprocessing.models import CentralizedFittedPreprocessingState
from datp_core.protocols.models import AutoencoderProtocol, CheckpointProtocol
from datp_core.runtime.compute import resolve_cuda_device


@dataclass(frozen=True, slots=True)
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
class TrainCentralizedReferenceResult:
    stage: StageOperationId
    publication_status: PublicationStatus
    training: CentralizedTrainingResult
    candidates: tuple[CentralizedCheckpointCandidate, ...]
    complete_digest: Checksum


def train_centralized_reference_stage(
    request: TrainCentralizedReferenceRequest,
) -> TrainCentralizedReferenceResult:
    require_no_hidden_scientific_defaults()
    training_protocol, _declared_autoencoder, learning_rate, batch_size, weight_decay = (
        declared_centralized_training_values()
    )
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

    holder: dict[str, CentralizedTrainingResult | tuple[CentralizedCheckpointCandidate, ...]] = {}

    def write(temporary: Path) -> None:
        training = train_centralized_autoencoder(
            CentralizedTrainingRequest(
                coordinate=request.coordinate,
                training_features=request.training_features,
                feature_names=request.feature_names,
                preprocessing_state=request.preprocessing_state,
                split_manifest_checksum=request.split_manifest_checksum,
                output_directory=temporary,
                training_seed=request.training_seed,
                autoencoder=request.autoencoder,
                training_protocol=training_protocol,
                checkpoint_protocol=request.checkpoint_protocol,
                learning_rate=learning_rate,
                batch_size=batch_size,
                benign_label=PopulationOutcomeLabel.BENIGN,
            )
        )
        candidates = retain_centralized_checkpoint_candidates(training, request.autoencoder)
        training_history_frame(training).write_parquet(temporary / CentralizedArtifactName.TRAINING_HISTORY)
        digest = _complete_digest(training)
        (temporary / CentralizedArtifactName.COMPLETE).write_text(digest.value, encoding="utf-8")
        holder["training"] = training
        holder["candidates"] = candidates

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
        training, candidates = _load_reused_training(
            request, training_protocol, learning_rate, batch_size, weight_decay
        )
        status = PublicationStatus.REUSED
    else:
        training = holder["training"]
        candidates = holder["candidates"]
        if not isinstance(training, CentralizedTrainingResult):
            raise ArtifactIntegrityError(
                "centralized training write failed to produce a result", subject=ContractSubject.TRAINING
            )
        if not isinstance(candidates, tuple):
            raise ArtifactIntegrityError(
                "centralized training write failed to produce candidates", subject=ContractSubject.CANDIDATES
            )
        # Re-bind paths from temporary directory to the final published directory.
        training = _rebase_training_paths(training, request.output_directory)
        candidates = _rebase_candidates(candidates, request.output_directory)
        status = PublicationStatus.PUBLISHED

    return TrainCentralizedReferenceResult(
        stage=StageOperationId.TRAIN_CENTRALIZED_REFERENCE,
        publication_status=status,
        training=training,
        candidates=candidates,
        complete_digest=checksum_file(request.output_directory / CentralizedArtifactName.COMPLETE),
    )


def _complete_digest(training: CentralizedTrainingResult) -> Checksum:
    return checksum_text(
        f"{training.model_tensor_checksum.value}|{training.final_epoch.value}|{training.batch_size_used.value}"
    )


def _is_reusable(directory: Path, request: TrainCentralizedReferenceRequest) -> bool:
    complete = directory / CentralizedArtifactName.COMPLETE
    model = directory / CentralizedArtifactName.MODEL_TENSORS
    history = directory / CentralizedArtifactName.TRAINING_HISTORY
    if not (complete.is_file() and model.is_file() and history.is_file()):
        return False
    for candidate in request.checkpoint_protocol.candidates:
        if not (directory / candidate_tensor_name(candidate)).is_file():
            return False
    try:
        expected = checksum_text(
            f"{checksum_file(model).value}|{request.checkpoint_protocol.maximum_round.value}|"
            f"{declared_centralized_training_values()[3].value}"
        )
        return complete.read_text(encoding="utf-8").strip() == expected.value
    except (OSError, ValueError):
        return False


def _load_reused_training(
    request: TrainCentralizedReferenceRequest,
    training_protocol,
    learning_rate,
    batch_size,
    weight_decay: WeightDecay,
) -> tuple[CentralizedTrainingResult, tuple[CentralizedCheckpointCandidate, ...]]:
    history = pl.read_parquet(request.output_directory / CentralizedArtifactName.TRAINING_HISTORY)
    epoch_losses = tuple(
        CentralizedEpochLoss(
            epoch=RoundNumber(int(epoch)),
            mean_training_loss=MetricValue(float(loss)),
        )
        for epoch, loss in history.select(
            [
                TrainingHistoryColumn.EPOCH.value,
                TrainingHistoryColumn.MEAN_TRAINING_LOSS.value,
            ]
        ).iter_rows()
    )
    loss_by_epoch = {item.epoch.value: item.mean_training_loss for item in epoch_losses}
    snapshots: list[CentralizedModelSnapshot] = []
    candidates: list[CentralizedCheckpointCandidate] = []
    for candidate_round in request.checkpoint_protocol.candidates:
        path = request.output_directory / candidate_tensor_name(candidate_round)
        if not path.is_file():
            raise ArtifactIntegrityError("reused checkpoint candidate missing", subject=ContractSubject.ARTIFACT_PATH)
        mean_loss = loss_by_epoch[candidate_round.value]
        snapshots.append(
            CentralizedModelSnapshot(
                round_number=candidate_round,
                state_dict={},
                mean_training_loss=mean_loss,
            )
        )
        candidates.append(
            CentralizedCheckpointCandidate(
                coordinate=request.coordinate,
                round_number=candidate_round,
                tensor_path=path,
                tensor_checksum=checksum_file(path),
                mean_training_loss=mean_loss,
                status=CheckpointStatus.CANDIDATE,
                preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
                split_manifest_checksum=request.split_manifest_checksum,
                training_seed=request.training_seed,
                autoencoder_widths=tuple(request.autoencoder.widths),
            )
        )
    model_path = request.output_directory / CentralizedArtifactName.MODEL_TENSORS
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
        candidate_snapshots=tuple(snapshots),
        model_directory=request.output_directory,
        model_tensor_path=model_path,
        model_tensor_checksum=checksum_file(model_path),
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=str(resolve_cuda_device()),
        batch_size_used=batch_size,
        final_epoch=request.checkpoint_protocol.maximum_round,
    )
    return training, tuple(candidates)


def _rebase_training_paths(training: CentralizedTrainingResult, directory: Path) -> CentralizedTrainingResult:
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
        candidate_snapshots=training.candidate_snapshots,
        model_directory=directory,
        model_tensor_path=directory / CentralizedArtifactName.MODEL_TENSORS,
        model_tensor_checksum=checksum_file(directory / CentralizedArtifactName.MODEL_TENSORS),
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
    rebased: list[CentralizedCheckpointCandidate] = []
    for candidate in candidates:
        path = directory / candidate_tensor_name(candidate.round_number)
        rebased.append(
            CentralizedCheckpointCandidate(
                coordinate=candidate.coordinate,
                round_number=candidate.round_number,
                tensor_path=path,
                tensor_checksum=checksum_file(path),
                mean_training_loss=candidate.mean_training_loss,
                status=candidate.status,
                preprocessing_state_checksum=candidate.preprocessing_state_checksum,
                split_manifest_checksum=candidate.split_manifest_checksum,
                training_seed=candidate.training_seed,
                autoencoder_widths=candidate.autoencoder_widths,
            )
        )
    return tuple(rebased)
