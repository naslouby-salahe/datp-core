"""Shared miniature fixtures for centralized-reference unit tests."""

from pathlib import Path

import numpy as np
import polars as pl
import torch

from datp_core.centralized_reference.training import (
    CentralizedTrainingCoordinate,
    CentralizedTrainingExecution,
    CentralizedTrainingRequest,
    train_centralized_autoencoder,
)
from datp_core.domain.enums import (
    CentralizedModelId,
    OptimizerId,
    PopulationId,
    PreprocessingFitScope,
    PreprocessingProtocolId,
    SerializationFormat,
    SplitProtocolId,
    TrustedEstimatorClassName,
)
from datp_core.domain.values import (
    NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    BatchSize,
    Checksum,
    FeatureName,
    FeatureNameSequence,
    LearningRate,
    OutcomeLabel,
    OutcomeLabelSequence,
    RoundNumber,
    RowCount,
    Seed,
    WeightDecay,
)
from datp_core.populations.models import OUTCOME_LABEL_COLUMN, STABLE_ROW_ID_COLUMN, PopulationOutcomeLabel
from datp_core.preprocessing.models import (
    CentralizedFittedPreprocessingState,
    PreprocessingProtocol,
)
from datp_core.protocols.models import (
    AutoencoderProtocol,
    CentralizedTrainingProtocol,
    CheckpointProtocol,
    OptimizerProtocol,
)

FEATURE_NAMES = FeatureNameSequence((FeatureName("f0"), FeatureName("f1"), FeatureName("f2"), FeatureName("f3")))
AUTOENCODER = AutoencoderProtocol(widths=(4, 3, 2, 3, 4))
CHECKPOINT = CheckpointProtocol(candidates=(RoundNumber(2),), maximum_round=RoundNumber(2))
TRAINING_PROTOCOL = CentralizedTrainingProtocol(
    kind=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    optimizer=OptimizerProtocol(identity=OptimizerId.ADAM, weight_decay=WeightDecay(0.0)),
)
LEARNING_RATE = LearningRate(0.001)
BATCH_SIZE = BatchSize(16)
SEED = Seed(0)
DEFAULT_EVALUATION_ROW_COUNT = RowCount(64)
DEFAULT_EVALUATION_SEED = Seed(1)


def feature_protocol() -> PreprocessingProtocol:
    return PreprocessingProtocol(
        identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        fit_scope=PreprocessingFitScope.POOLED_TRAINING,
        input_feature_names=FEATURE_NAMES,
        serialization_format=SerializationFormat.SKOPS,
        estimator_class_name=TrustedEstimatorClassName.MIN_MAX_SCALER,
        numerical_equivalence_absolute_tolerance=NUMERICAL_EQUIVALENCE_ABSOLUTE_TOLERANCE,
    )


def training_coordinate() -> CentralizedTrainingCoordinate:
    return CentralizedTrainingCoordinate(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        training_seed=SEED,
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.CENTRALIZED_POOLED_MIN_MAX,
        model=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    )


def fitted_state(path: Path) -> CentralizedFittedPreprocessingState:
    protocol = feature_protocol()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"placeholder")
    return CentralizedFittedPreprocessingState(
        protocol=protocol,
        estimator_path=path,
        estimator_checksum=Checksum("a" * 64),
        fit_row_count=RowCount(64),
    )


def benign_frame(
    row_count: RowCount,
    *,
    seed: Seed = SEED,
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


def mixed_evaluation_frame(
    row_count: RowCount = DEFAULT_EVALUATION_ROW_COUNT,
    *,
    seed: Seed = DEFAULT_EVALUATION_SEED,
) -> pl.DataFrame:
    half = RowCount(row_count.value // 2)
    benign = benign_frame(half, seed=seed, label=PopulationOutcomeLabel.BENIGN.value)
    attack = benign_frame(
        RowCount(row_count.value - half.value),
        seed=Seed(seed.value + 1),
        label=PopulationOutcomeLabel.ATTACK.value,
    )
    attack = attack.with_columns((pl.col("f0") + 4.0).alias("f0"))
    return pl.concat([benign, attack], how="vertical")


def run_miniature_training(output_directory: Path) -> CentralizedTrainingExecution:
    state = fitted_state(output_directory / "state.skops")
    return train_centralized_autoencoder(
        CentralizedTrainingRequest(
            coordinate=training_coordinate(),
            training_features=benign_frame(RowCount(64), seed=Seed(0)),
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
            benign_label=PopulationOutcomeLabel.BENIGN,
        )
    )


def require_cuda() -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError("centralized tests require CUDA")
    return torch.device("cuda")


def benign_labels(count: int) -> OutcomeLabelSequence:
    return OutcomeLabelSequence(tuple(OutcomeLabel(PopulationOutcomeLabel.BENIGN.value) for _ in range(count)))
