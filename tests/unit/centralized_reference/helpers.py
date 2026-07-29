"""Shared miniature fixtures for centralized-reference unit tests."""

from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp_core.centralized_reference.training import (
    CentralizedTrainingCoordinate,
    CentralizedTrainingRequest,
    CentralizedTrainingResult,
    train_centralized_autoencoder,
)
from datp_core.domain.enums import (
    CentralizedModelId,
    OptimizerId,
    PartitionRole,
    PopulationId,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SerializationFormat,
    SplitProtocolId,
    TrustedEstimatorClassName,
    TrustedEstimatorModule,
)
from datp_core.domain.values import (
    BatchSize,
    Checksum,
    FeatureNameSequence,
    LearningRate,
    OutcomeLabelSequence,
    RoundNumber,
    Seed,
    WeightDecay,
)
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN, PopulationOutcomeLabel
from datp_core.preprocessing.models import (
    FittedPreprocessingState,
    PreprocessingProtocol,
    TransformedFeature,
    TransformedSchema,
)
from datp_core.protocols.anchor import FIXED_SCORE_ABSOLUTE_TOLERANCE
from datp_core.protocols.models import (
    AutoencoderProtocol,
    CentralizedTrainingProtocol,
    CheckpointProtocol,
    OptimizerProtocol,
)

FEATURE_NAMES = FeatureNameSequence(("f0", "f1", "f2", "f3"))
AUTOENCODER = AutoencoderProtocol(widths=(4, 3, 2, 3, 4))
CHECKPOINT = CheckpointProtocol(candidates=(RoundNumber(2),), maximum_round=RoundNumber(2))
TRAINING_PROTOCOL = CentralizedTrainingProtocol(
    kind=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    optimizer=OptimizerProtocol(identity=OptimizerId.ADAM, weight_decay=WeightDecay(0.0)),
)
LEARNING_RATE = LearningRate(0.001)
BATCH_SIZE = BatchSize(16)
SEED = Seed(0)


def feature_protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        fit_scope=PreprocessingFitScope.POOLED_TRAINING,
        input_feature_names=FEATURE_NAMES.names,
        transformed_schema=TransformedSchema(
            features=tuple(
                TransformedFeature(name=name, position=index) for index, name in enumerate(FEATURE_NAMES.names)
            )
        ),
        serialization_format=SerializationFormat.SKOPS,
        estimator_module=TrustedEstimatorModule.SKLEARN_PREPROCESSING,
        estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
        numerical_equivalence_absolute_tolerance=FIXED_SCORE_ABSOLUTE_TOLERANCE.value,
    )


def training_coordinate() -> CentralizedTrainingCoordinate:
    return CentralizedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=SEED,
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        model=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    )


def fitted_state(path: Path) -> FittedPreprocessingState:
    protocol = feature_protocol()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")
    return FittedPreprocessingState(
        protocol=protocol,
        branch=ProcessedDataBranch.CENTRALIZED_REFERENCE,
        client_identity=None,
        estimator_path=path,
        estimator_checksum=Checksum("a" * 64),
        transformed_schema=protocol.transformed_schema,
        fit_row_count=64,
        fit_partition=PartitionRole.TRAIN,
    )


def benign_frame(row_count: int, *, seed: int = 0, label: str = PopulationOutcomeLabel.BENIGN.value) -> pl.DataFrame:
    generator = np.random.default_rng(seed)
    matrix = generator.normal(size=(row_count, len(FEATURE_NAMES))).astype(np.float32)
    return pl.DataFrame(
        {
            STABLE_ROW_ID_COLUMN: [f"row-{seed}-{index}" for index in range(row_count)],
            OUTCOME_LABEL_COLUMN: [label] * row_count,
            **{name: matrix[:, index] for index, name in enumerate(FEATURE_NAMES.names)},
        }
    )


def mixed_evaluation_frame(row_count: int = 64, *, seed: int = 1) -> pl.DataFrame:
    half = row_count // 2
    benign = benign_frame(half, seed=seed, label=PopulationOutcomeLabel.BENIGN.value)
    attack = benign_frame(row_count - half, seed=seed + 1, label=PopulationOutcomeLabel.ATTACK.value)
    attack = attack.with_columns((pl.col("f0") + 4.0).alias("f0"))
    return pl.concat([benign, attack], how="vertical")


def run_miniature_training(output_directory: Path) -> CentralizedTrainingResult:
    state = fitted_state(output_directory / "state.skops")
    return train_centralized_autoencoder(
        CentralizedTrainingRequest(
            coordinate=training_coordinate(),
            training_features=benign_frame(64, seed=0),
            feature_names=FEATURE_NAMES,
            preprocessing_state=state,
            split_manifest_checksum=Checksum("b" * 64),
            output_directory=output_directory,
            training_seed=SEED,
            autoencoder=AUTOENCODER,
            training_protocol=TRAINING_PROTOCOL,
            checkpoint_protocol=CHECKPOINT,
            learning_rate=LEARNING_RATE,
            batch_size=BATCH_SIZE,
        )
    )


def require_cuda() -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError("Phase 07 centralized tests require CUDA")
    return torch.device("cuda")


def benign_labels(count: int) -> OutcomeLabelSequence:
    return OutcomeLabelSequence(tuple(PopulationOutcomeLabel.BENIGN.value for _ in range(count)))
