"""Independent centralized autoencoder training for the privacy-incompatible reference."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np
import polars as pl
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.artifacts.provenance import Checksum
from datp_core.artifacts.serializers.safetensors import load_state_dict_tensors, save_state_dict_tensors
from datp_core.core.errors import (
    ArtifactIntegrityError,
    ErrorMessage,
    ExecutionStateError,
    LeakageError,
    ScientificContractError,
    UnresolvedScientificValueError,
)
from datp_core.core.identifiers import (
    CentralizedModelId,
    ContractSubject,
    CudaDeviceName,
    FeatureNameSequence,
    OptimizerId,
    OutcomeLabel,
    OutcomeLabelSequence,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SplitProtocolId,
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
from datp_core.data.populations.contracts import (
    OUTCOME_LABEL_COLUMN,
    PopulationFrameColumn,
    PopulationOutcomeLabel,
)
from datp_core.data.preprocessing.models import (
    CentralizedFittedPreprocessingState,
    FederatedFittedPreprocessingState,
    FittedPreprocessingState,
)
from datp_core.detector.autoencoder import (
    LEARNING_DTYPE,
    TORCH_LEARNING_DTYPE,
    AutoencoderState,
    ReconstructionAutoencoder,
    build_optimizer,
    construct_autoencoder,
)
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.training.contracts import (
    AutoencoderArchitecture,
    AutoencoderProtocol,
    CentralizedTrainingProtocol,
)
from datp_core.detector.training.protocols import (
    BATCH_SIZE,
    CENTRALIZED_DATALOADER_WORKER_COUNT,
    CENTRALIZED_TRAINING_PROTOCOL,
    LEARNING_RATE,
    NBAIOT_AUTOENCODER,
    WEIGHT_DECAY,
)
from datp_core.runtime.compute import require_cuda_available, resolve_cuda_device
from datp_core.runtime.determinism import configure_deterministic_execution


class CentralizedArtifactName(StrEnum):
    MODEL_TENSORS = "model.safetensors"
    TRAINING_HISTORY = "training_history.parquet"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class CentralizedTrainingCoordinate:
    population: PopulationId
    training_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    model: CentralizedModelId

    def __post_init__(self) -> None:
        if self.model is not CentralizedModelId.CENTRALIZED_AUTOENCODER:
            raise ScientificContractError(
                ErrorMessage("centralized training requires CENTRALIZED_AUTOENCODER"),
                subject=self.model,
            )


@dataclass(frozen=True, slots=True)
class CentralizedOptimizerSummary:
    identity: OptimizerId
    learning_rate: LearningRate
    weight_decay: WeightDecay
    batch_size: BatchSize


@dataclass(frozen=True, slots=True)
class CentralizedEpochLoss:
    epoch: RoundNumber
    mean_training_loss: MetricValue


@dataclass(frozen=True, slots=True, eq=False)
class InMemoryCentralizedModelSnapshot:
    """Transient model state captured only during one training execution."""

    round_number: RoundNumber
    state_dict: AutoencoderState
    mean_training_loss: MetricValue


@dataclass(frozen=True, slots=True)
class CentralizedTrainingResult:
    """Persistable centralized training result with no fabricated in-memory tensor state."""

    coordinate: CentralizedTrainingCoordinate
    autoencoder_widths: AutoencoderArchitecture
    optimizer: CentralizedOptimizerSummary
    checkpoint_protocol: CheckpointProtocol
    training_protocol: CentralizedTrainingProtocol
    training_seed: Seed
    train_row_count: RowCount
    feature_count: FeatureCount
    epoch_losses: tuple[CentralizedEpochLoss, ...]
    model_directory: Path
    model_tensor_path: Path
    model_tensor_checksum: Checksum
    preprocessing_state_checksum: Checksum
    split_manifest_checksum: Checksum
    device_name: CudaDeviceName
    batch_size_used: BatchSize
    final_epoch: RoundNumber

    def __post_init__(self) -> None:
        if self.train_row_count.value < 1:
            raise ValueError("centralized training requires at least one benign training row")
        if self.batch_size_used != self.optimizer.batch_size:
            raise ScientificContractError(
                ErrorMessage("recorded batch size must equal the declared optimizer batch size"),
                subject=ContractSubject.BATCH_SIZE,
            )
        if self.final_epoch != self.checkpoint_protocol.maximum_round:
            raise ScientificContractError(
                ErrorMessage("centralized training terminal epoch must equal the declared maximum round"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )


@dataclass(frozen=True, slots=True)
class CentralizedTrainingExecution:
    """One live training execution plus transient checkpoint snapshots."""

    result: CentralizedTrainingResult
    candidate_snapshots: tuple[InMemoryCentralizedModelSnapshot, ...]

    def __post_init__(self) -> None:
        observed = tuple(snapshot.round_number for snapshot in self.candidate_snapshots)
        if observed != self.result.checkpoint_protocol.candidates:
            raise ScientificContractError(
                ErrorMessage("in-memory checkpoint snapshots must match the declared candidate rounds"),
                subject=ContractSubject.CHECKPOINT_CANDIDATES,
            )


@dataclass(frozen=True, slots=True, eq=False)
class CentralizedTrainingRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    split_manifest_checksum: Checksum
    output_directory: Path
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    training_protocol: CentralizedTrainingProtocol
    checkpoint_protocol: CheckpointProtocol
    learning_rate: LearningRate
    batch_size: BatchSize
    benign_label: PopulationOutcomeLabel


def reject_federated_preprocessing_for_training(state: FittedPreprocessingState) -> None:
    if isinstance(state, FederatedFittedPreprocessingState):
        raise LeakageError(
            ErrorMessage("federated preprocessing state cannot enter centralized training"),
            subject=ProcessedDataBranch.FEDERATED,
        )


def reject_attack_rows_in_centralized_training(
    labels: OutcomeLabelSequence,
    benign_label: PopulationOutcomeLabel,
) -> None:
    if any(label != benign_label for label in labels):
        raise LeakageError(
            ErrorMessage("attack-labelled rows cannot enter centralized benign training"),
            subject=ContractSubject.LABEL,
        )


def train_centralized_autoencoder(request: CentralizedTrainingRequest) -> CentralizedTrainingExecution:
    """Train the independent pooled autoencoder on CUDA with declared hyperparameters."""
    _validate_training_request(request)
    reject_federated_preprocessing_for_training(request.preprocessing_state)
    configure_deterministic_execution(request.training_seed)
    device = resolve_cuda_device()
    extracted = _extract_training_arrays(request)
    reject_attack_rows_in_centralized_training(extracted.labels, request.benign_label)
    if extracted.feature_matrix.shape[1] != request.autoencoder.widths[0].value:
        raise ScientificContractError(
            ErrorMessage("feature width must match the declared autoencoder input width"),
            subject=ContractSubject.FEATURES,
        )
    if extracted.feature_matrix.shape[0] < request.batch_size.value:
        raise ScientificContractError(
            ErrorMessage("centralized training requires at least one full declared batch"),
            subject=ContractSubject.BATCH_SIZE,
        )

    model = construct_autoencoder(request.autoencoder).to(device)
    optimizer = build_optimizer(model, request.training_protocol.optimizer, request.learning_rate)
    loader = _build_loader(
        extracted.feature_matrix,
        batch_size=request.batch_size,
        seed=request.training_seed,
    )
    epoch_losses, snapshots = _run_training_epochs(
        model=model,
        optimizer=optimizer,
        loader=loader,
        checkpoint_protocol=request.checkpoint_protocol,
        device=device,
    )
    request.output_directory.mkdir(parents=True, exist_ok=True)
    tensor_path = request.output_directory / CentralizedArtifactName.MODEL_TENSORS
    tensor_checksum = save_state_dict_tensors(model.state_dict(), tensor_path)
    assert_safetensors_reload(model, tensor_path, device)
    result = CentralizedTrainingResult(
        coordinate=request.coordinate,
        autoencoder_widths=request.autoencoder.widths,
        optimizer=CentralizedOptimizerSummary(
            identity=request.training_protocol.optimizer.identity,
            learning_rate=request.learning_rate,
            weight_decay=request.training_protocol.optimizer.weight_decay,
            batch_size=request.batch_size,
        ),
        checkpoint_protocol=request.checkpoint_protocol,
        training_protocol=request.training_protocol,
        training_seed=request.training_seed,
        train_row_count=RowCount(int(extracted.feature_matrix.shape[0])),
        feature_count=FeatureCount(int(extracted.feature_matrix.shape[1])),
        epoch_losses=epoch_losses,
        model_directory=request.output_directory,
        model_tensor_path=tensor_path,
        model_tensor_checksum=tensor_checksum,
        preprocessing_state_checksum=request.preprocessing_state.estimator_checksum,
        split_manifest_checksum=request.split_manifest_checksum,
        device_name=CudaDeviceName(torch.cuda.get_device_name(device)),
        batch_size_used=request.batch_size,
        final_epoch=request.checkpoint_protocol.maximum_round,
    )
    return CentralizedTrainingExecution(result=result, candidate_snapshots=snapshots)


def load_centralized_model_tensors(
    path: Path,
    autoencoder: AutoencoderProtocol,
    device: torch.device | None = None,
) -> ReconstructionAutoencoder:
    require_cuda_available()
    resolved = resolve_cuda_device() if device is None else device
    if resolved.type != "cuda":
        raise ExecutionStateError(ErrorMessage("centralized model reload requires CUDA"), subject=ContractSubject.CUDA)
    model = construct_autoencoder(autoencoder).to(resolved)
    state = load_state_dict_tensors(path, resolved)
    model.load_state_dict(state, strict=True)
    model.eval()
    return model


def model_from_in_memory_snapshot(
    snapshot: InMemoryCentralizedModelSnapshot,
    autoencoder: AutoencoderProtocol,
    device: torch.device | None = None,
) -> ReconstructionAutoencoder:
    require_cuda_available()
    resolved = resolve_cuda_device() if device is None else device
    model = construct_autoencoder(autoencoder).to(resolved)
    model.load_state_dict(snapshot.state_dict, strict=True)
    model.eval()
    return model


def declared_centralized_training_values() -> tuple[
    CentralizedTrainingProtocol,
    AutoencoderProtocol,
    LearningRate,
    BatchSize,
    WeightDecay,
]:
    return CENTRALIZED_TRAINING_PROTOCOL, NBAIOT_AUTOENCODER, LEARNING_RATE, BATCH_SIZE, WEIGHT_DECAY


def assert_safetensors_reload(
    model: ReconstructionAutoencoder,
    path: Path,
    device: torch.device,
) -> None:
    reloaded = construct_autoencoder(AutoencoderProtocol(widths=model.widths)).to(device)
    state = load_state_dict_tensors(path, device)
    reloaded.load_state_dict(state, strict=True)
    for left, right in zip(model.state_dict().values(), reloaded.state_dict().values(), strict=True):
        if not torch.equal(left, right):
            raise ArtifactIntegrityError(
                ErrorMessage("SafeTensors reload does not match saved centralized weights"),
                subject=ContractSubject.ARTIFACT_PATH,
            )


def training_history_frame(result: CentralizedTrainingResult) -> pl.DataFrame:
    return pl.DataFrame(
        (
            pl.Series(
                TrainingHistoryColumn.EPOCH.value,
                tuple(item.epoch.value for item in result.epoch_losses),
            ),
            pl.Series(
                TrainingHistoryColumn.MEAN_TRAINING_LOSS.value,
                tuple(item.mean_training_loss.value for item in result.epoch_losses),
            ),
        )
    )


def require_no_hidden_scientific_defaults() -> None:
    """Fail if mandatory centralized training values are absent from declarations."""
    if CENTRALIZED_TRAINING_PROTOCOL.optimizer.identity is not OptimizerId.ADAM:
        raise UnresolvedScientificValueError(
            ErrorMessage("centralized optimizer identity is not the declared Adam protocol"),
            subject=ContractSubject.OPTIMIZER,
        )
    if LEARNING_RATE.value <= 0 or BATCH_SIZE.value <= 0:
        raise UnresolvedScientificValueError(
            ErrorMessage("centralized learning rate or batch size is unresolved"),
            subject=ContractSubject.TRAINING_HYPERPARAMETERS,
        )
    if WEIGHT_DECAY.value < 0:
        raise UnresolvedScientificValueError(
            ErrorMessage("centralized Adam weight decay is unresolved"),
            subject=ContractSubject.TRAINING_HYPERPARAMETERS,
        )
    if not NBAIOT_AUTOENCODER.widths:
        raise UnresolvedScientificValueError(
            ErrorMessage("centralized autoencoder widths are unresolved"),
            subject=ContractSubject.AUTOENCODER,
        )


def _validate_training_request(request: CentralizedTrainingRequest) -> None:
    _require_centralized_model_identities(request)
    _require_training_frame_schema(request)


def _require_centralized_model_identities(request: CentralizedTrainingRequest) -> None:
    if request.training_protocol.kind is not CentralizedModelId.CENTRALIZED_AUTOENCODER:
        raise ScientificContractError(
            ErrorMessage("training protocol must declare CENTRALIZED_AUTOENCODER"),
            subject=request.training_protocol.kind,
        )
    if request.coordinate.model is not CentralizedModelId.CENTRALIZED_AUTOENCODER:
        raise ScientificContractError(
            ErrorMessage("training coordinate model identity is invalid"),
            subject=request.coordinate.model,
        )
    if request.preprocessing_state.protocol.identity is not request.coordinate.preprocessing_identity:
        raise ScientificContractError(
            ErrorMessage("preprocessing identity mismatch between coordinate and fitted state"),
            subject=ContractSubject.PREPROCESSING,
        )


def _require_training_frame_schema(request: CentralizedTrainingRequest) -> None:
    missing = tuple(name for name in request.feature_names if name not in request.training_features.columns)
    if missing:
        raise ScientificContractError(
            ErrorMessage(f"training frame missing declared features: {', '.join(missing)}"),
            subject=ContractSubject.FEATURES,
        )
    for column in (PopulationFrameColumn.STABLE_ROW_ID, PopulationFrameColumn.OUTCOME_LABEL):
        if column.value not in request.training_features.columns:
            raise ScientificContractError(
                ErrorMessage(f"training frame missing required column {column.value}"),
                subject=column,
            )


@dataclass(frozen=True, slots=True)
class _ExtractedTrainingArrays:
    feature_matrix: np.ndarray
    labels: OutcomeLabelSequence


def _extract_training_arrays(
    request: CentralizedTrainingRequest,
) -> _ExtractedTrainingArrays:
    frame = request.training_features
    labels = OutcomeLabelSequence(
        tuple(OutcomeLabel(str(value)) for value in frame.get_column(OUTCOME_LABEL_COLUMN).to_list())
    )
    matrix = frame.select(request.feature_names.as_list()).to_numpy().astype(LEARNING_DTYPE, copy=False)
    if not np.isfinite(matrix).all():
        raise ScientificContractError(
            ErrorMessage("centralized training features must be finite"),
            subject=ContractSubject.FEATURES,
        )
    if len(labels) != matrix.shape[0]:
        raise ScientificContractError(ErrorMessage("training arrays must align by row"), subject=ContractSubject.ROWS)
    return _ExtractedTrainingArrays(feature_matrix=matrix, labels=labels)


def _build_loader(
    matrix: np.ndarray,
    *,
    batch_size: BatchSize,
    seed: Seed,
) -> DataLoader[tuple[torch.Tensor, ...]]:
    require_cuda_available()
    tensor = torch.tensor(matrix, dtype=TORCH_LEARNING_DTYPE)
    dataset = TensorDataset(tensor)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed.value)
    return DataLoader(
        dataset,
        batch_size=batch_size.value,
        shuffle=True,
        drop_last=True,
        generator=generator,
        num_workers=CENTRALIZED_DATALOADER_WORKER_COUNT.value,
        pin_memory=True,
    )


def _run_training_epochs(
    *,
    model: ReconstructionAutoencoder,
    optimizer: torch.optim.Optimizer,
    loader: DataLoader[tuple[torch.Tensor, ...]],
    checkpoint_protocol: CheckpointProtocol,
    device: torch.device,
) -> tuple[  # TODO: should be handled better instead of tuple of tuple and tuple
    tuple[CentralizedEpochLoss, ...],
    tuple[InMemoryCentralizedModelSnapshot, ...],
]:
    losses: list[CentralizedEpochLoss] = []
    snapshots: list[InMemoryCentralizedModelSnapshot] = []
    candidate_rounds = frozenset(candidate.value for candidate in checkpoint_protocol.candidates)
    model.train()

    for epoch_index in range(1, checkpoint_protocol.maximum_round.value + 1):
        running_loss = 0.0
        batch_count = 0

        for (batch,) in loader:
            batch = batch.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            reconstruction = model(batch)
            loss = nn.functional.mse_loss(reconstruction, batch)
            torch.autograd.backward(loss)
            optimizer.step()
            running_loss += loss.item()
            batch_count += 1

        if batch_count == 0:
            raise ScientificContractError(
                ErrorMessage("centralized training produced no batches; declared batch size cannot be relaxed"),
                subject=ContractSubject.BATCH_SIZE,
            )

        mean_loss = MetricValue(running_loss / batch_count)
        epoch = RoundNumber(epoch_index)
        losses.append(CentralizedEpochLoss(epoch=epoch, mean_training_loss=mean_loss))

        if epoch_index in candidate_rounds:
            snapshots.append(
                InMemoryCentralizedModelSnapshot(
                    round_number=epoch,
                    state_dict={name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()},
                    mean_training_loss=mean_loss,
                )
            )

    expected = tuple(candidate.value for candidate in checkpoint_protocol.candidates)
    observed = tuple(item.round_number.value for item in snapshots)
    if observed != expected:
        raise ScientificContractError(
            ErrorMessage("training failed to capture every declared checkpoint candidate"),
            subject=ContractSubject.CHECKPOINT_CANDIDATES,
        )
    return tuple(losses), tuple(snapshots)
