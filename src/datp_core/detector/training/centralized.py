from dataclasses import dataclass

import numpy as np
import polars as pl
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.core.errors import (
    ErrorMessage,
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
    AutoencoderModelState,
    ReconstructionAutoencoder,
    build_optimizer,
    construct_autoencoder,
)
from datp_core.detector.checkpoints.contracts import DiagnosticSnapshotProtocol
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
class CentralizedTrainingDefaults:
    training_protocol: CentralizedTrainingProtocol
    autoencoder: AutoencoderProtocol
    learning_rate: LearningRate
    batch_size: BatchSize
    weight_decay: WeightDecay


@dataclass(frozen=True, slots=True)
class CentralizedEpochLoss:
    epoch: RoundNumber
    mean_training_loss: MetricValue


@dataclass(frozen=True, slots=True)
class TrainingEpochResults:
    epoch_losses: tuple[CentralizedEpochLoss, ...]


@dataclass(frozen=True, slots=True)
class CentralizedTrainingResult:
    coordinate: CentralizedTrainingCoordinate
    autoencoder_widths: AutoencoderArchitecture
    optimizer: CentralizedOptimizerSummary
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol
    training_protocol: CentralizedTrainingProtocol
    training_seed: Seed
    train_row_count: RowCount
    feature_count: FeatureCount
    epoch_losses: tuple[CentralizedEpochLoss, ...]
    terminal_model_state: AutoencoderModelState
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
        if self.final_epoch != self.diagnostic_snapshot_protocol.maximum_round:
            raise ScientificContractError(
                ErrorMessage("centralized training terminal epoch must equal the declared maximum round"),
                subject=ContractSubject.TRAINING,
            )


@dataclass(frozen=True, slots=True)
class CentralizedTrainingExecution:
    result: CentralizedTrainingResult


@dataclass(frozen=True, slots=True, eq=False)
class CentralizedTrainingRequest:
    coordinate: CentralizedTrainingCoordinate
    training_features: pl.DataFrame
    feature_names: FeatureNameSequence
    preprocessing_state: CentralizedFittedPreprocessingState
    training_seed: Seed
    autoencoder: AutoencoderProtocol
    training_protocol: CentralizedTrainingProtocol
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol
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
    training_results = _run_training_epochs(
        model=model,
        optimizer=optimizer,
        loader=loader,
        diagnostic_snapshot_protocol=request.diagnostic_snapshot_protocol,
        device=device,
    )
    model_state = AutoencoderModelState.from_model(model)
    result = CentralizedTrainingResult(
        coordinate=request.coordinate,
        autoencoder_widths=request.autoencoder.widths,
        optimizer=CentralizedOptimizerSummary(
            identity=request.training_protocol.optimizer.identity,
            learning_rate=request.learning_rate,
            weight_decay=request.training_protocol.optimizer.weight_decay,
            batch_size=request.batch_size,
        ),
        diagnostic_snapshot_protocol=request.diagnostic_snapshot_protocol,
        training_protocol=request.training_protocol,
        training_seed=request.training_seed,
        train_row_count=RowCount(int(extracted.feature_matrix.shape[0])),
        feature_count=FeatureCount(int(extracted.feature_matrix.shape[1])),
        epoch_losses=training_results.epoch_losses,
        terminal_model_state=model_state,
        device_name=CudaDeviceName(torch.cuda.get_device_name(device)),
        batch_size_used=request.batch_size,
        final_epoch=request.diagnostic_snapshot_protocol.maximum_round,
    )
    return CentralizedTrainingExecution(result=result)


def declared_centralized_training_values() -> CentralizedTrainingDefaults:
    return CentralizedTrainingDefaults(
        training_protocol=CENTRALIZED_TRAINING_PROTOCOL,
        autoencoder=NBAIOT_AUTOENCODER,
        learning_rate=LEARNING_RATE,
        batch_size=BATCH_SIZE,
        weight_decay=WEIGHT_DECAY,
    )


def require_no_hidden_scientific_defaults() -> None:

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
    diagnostic_snapshot_protocol: DiagnosticSnapshotProtocol,
    device: torch.device,
) -> TrainingEpochResults:
    losses: list[CentralizedEpochLoss] = []
    model.train()

    for epoch_index in range(1, diagnostic_snapshot_protocol.maximum_round.value + 1):
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

    return TrainingEpochResults(epoch_losses=tuple(losses))
