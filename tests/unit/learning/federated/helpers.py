"""Shared miniature fixtures for federated learning unit tests."""

from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import ClientPathToken as PreprocessingClientIdentity
from datp_core.core.identifiers import (
    FeatureName,
    FeatureNameSequence,
    OptimizerId,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    SerializationFormat,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    BatchSize,
    ClientCount,
    DittoRegularization,
    FeatureCount,
    LearningRate,
    LocalEpochCount,
    ProximalCoefficient,
    RoundNumber,
    RowCount,
    Seed,
)
from datp_core.data.populations.contracts import (
    OUTCOME_LABEL_COLUMN,
    STABLE_ROW_ID_COLUMN,
    ClientIdentity,
    PopulationOutcomeLabel,
)
from datp_core.data.preprocessing.artifacts import PreprocessingFitScope, TrustedEstimatorClassName
from datp_core.data.preprocessing.models import (
    FederatedFittedPreprocessingState,
    PreprocessingProtocol,
)
from datp_core.detector.checkpoints.contracts import CheckpointProtocol
from datp_core.detector.training.contracts import (
    AutoencoderArchitecture,
    AutoencoderProtocol,
    DittoProtocol,
    FedAvgProtocol,
    FedProxProtocol,
    OptimizerProtocol,
)
from datp_core.detector.training.models import (
    ClientTrainingInput,
    DittoTrainingCoordinates,
    FederatedTrainingCoordinate,
)
from datp_core.protocols.training import (
    DITTO_REGULARIZATION_GRID,
    WEIGHT_DECAY,
)

FEATURE_NAMES = FeatureNameSequence((FeatureName("f0"), FeatureName("f1"), FeatureName("f2"), FeatureName("f3")))
AUTOENCODER = AutoencoderProtocol(
    widths=AutoencoderArchitecture(
        (FeatureCount(4), FeatureCount(3), FeatureCount(2), FeatureCount(3), FeatureCount(4))
    )
)
CHECKPOINT = CheckpointProtocol(candidates=(RoundNumber(1), RoundNumber(2)), maximum_round=RoundNumber(2))
LEARNING_RATE = LearningRate(0.01)
BATCH_SIZE = BatchSize(4)
POPULATION = PopulationId.NBAIOT_NATURAL_DEVICES
SPLIT_PROTOCOL = SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
PREPROCESSING_IDENTITY = PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD
CLIENT_IDS = ("client_a", "client_b")
POPULATION_CLIENT_COUNT = ClientCount(len(CLIENT_IDS))
DEFAULT_CLIENT_ROW_COUNT = RowCount(16)
DEFAULT_FRAME_SEED = Seed(0)

OPTIMIZER = OptimizerProtocol(identity=OptimizerId.ADAM, weight_decay=WEIGHT_DECAY)
LOCAL_EPOCHS = LocalEpochCount(1)
FEDAVG_PROTOCOL = FedAvgProtocol(
    kind=TrainingModelId.FEDAVG_AUTOENCODER, local_epochs=LOCAL_EPOCHS, optimizer=OPTIMIZER
)


def fedavg_coordinate(seed: Seed) -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=POPULATION,
        training_seed=seed,
        split_protocol=SPLIT_PROTOCOL,
        preprocessing_identity=PREPROCESSING_IDENTITY,
        model=TrainingModelId.FEDAVG_AUTOENCODER,
        model_coefficient=None,
    )


def fedprox_coordinate(seed: Seed, coefficient: ProximalCoefficient) -> FederatedTrainingCoordinate:
    return FederatedTrainingCoordinate(
        population=POPULATION,
        training_seed=seed,
        split_protocol=SPLIT_PROTOCOL,
        preprocessing_identity=PREPROCESSING_IDENTITY,
        model=TrainingModelId.FEDPROX_AUTOENCODER,
        model_coefficient=coefficient,
    )


def fedprox_protocol(coefficient: ProximalCoefficient) -> FedProxProtocol:
    return FedProxProtocol(
        kind=TrainingModelId.FEDPROX_AUTOENCODER,
        local_epochs=LOCAL_EPOCHS,
        optimizer=OPTIMIZER,
        coefficient=coefficient,
    )


def ditto_coordinates(
    seed: Seed,
) -> tuple[DittoTrainingCoordinates, DittoRegularization]:
    regularization = DITTO_REGULARIZATION_GRID[1]
    coordinates = DittoTrainingCoordinates.create(
        population=POPULATION,
        training_seed=seed,
        split_protocol=SPLIT_PROTOCOL,
        preprocessing_identity=PREPROCESSING_IDENTITY,
        regularization=regularization,
    )
    return coordinates, regularization


def ditto_protocol(regularization: DittoRegularization) -> DittoProtocol:
    return DittoProtocol(
        kind=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        local_epochs=LOCAL_EPOCHS,
        optimizer=OPTIMIZER,
        regularization=regularization,
    )


def feature_protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
        fit_scope=PreprocessingFitScope.CLIENT_LOCAL_TRAINING,
        input_feature_names=FEATURE_NAMES,
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    )


def client_identity(client_id: str) -> ClientIdentity:
    return ClientIdentity(POPULATION, client_id, PopulationIdentityKind.PHYSICAL_DEVICES)


def fitted_state(path: Path, client_id: str, *, checksum_suffix: str = "a") -> FederatedFittedPreprocessingState:
    protocol = feature_protocol()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")
    return FederatedFittedPreprocessingState(
        protocol=protocol,
        client_identity=PreprocessingClientIdentity(client_id),
        estimator_path=path,
        estimator_checksum=Checksum((checksum_suffix * 64)[:64]),
        fit_row_count=RowCount(32),
    )


def benign_frame(
    row_count: RowCount,
    *,
    seed: Seed = DEFAULT_FRAME_SEED,
    label: str = PopulationOutcomeLabel.BENIGN.value,
) -> pl.DataFrame:
    generator = np.random.default_rng(seed.value)
    matrix = generator.normal(size=(row_count.value, len(FEATURE_NAMES))).astype(np.float32)
    return pl.DataFrame(
        {
            STABLE_ROW_ID_COLUMN: [f"row-{seed.value}-{index}" for index in range(row_count.value)],
            OUTCOME_LABEL_COLUMN: [label] * row_count.value,
            **{name: matrix[:, index] for index, name in enumerate(FEATURE_NAMES.names)},
        }
    )


def build_client_input(
    client_id: str,
    output_directory: Path,
    *,
    row_count: RowCount = DEFAULT_CLIENT_ROW_COUNT,
    seed: Seed = DEFAULT_FRAME_SEED,
) -> ClientTrainingInput:
    state = fitted_state(output_directory / f"{client_id}_state.skops", client_id, checksum_suffix=client_id[-1])
    return ClientTrainingInput(
        client=client_identity(client_id),
        training_features=benign_frame(row_count, seed=seed),
        feature_names=FEATURE_NAMES,
        preprocessing_state=state,
    )


def build_all_client_inputs(output_directory: Path) -> tuple[ClientTrainingInput, ...]:
    return tuple(
        build_client_input(client_id, output_directory, seed=Seed(index)) for index, client_id in enumerate(CLIENT_IDS)
    )


def require_cuda() -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError("federated tests require CUDA")
    return torch.device("cuda")
