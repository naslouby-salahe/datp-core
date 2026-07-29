"""Training declarations."""

from datp_core.domain.enums import CentralizedModelId, CheckpointSelectionRule, OptimizerId, TrainingModelId
from datp_core.domain.values import (
    BatchSize,
    DataLoaderWorkerCount,
    DittoRegularization,
    LearningRate,
    LocalEpochCount,
    MetricValue,
    ProximalCoefficient,
    Ratio,
    RoundNumber,
    WeightDecay,
)

from .models import (
    AutoencoderProtocol,
    CentralizedTrainingProtocol,
    CheckpointProtocol,
    DittoProtocol,
    FedAvgProtocol,
    FedProxProtocol,
    OptimizerProtocol,
)

CHECKPOINT_PROTOCOL = CheckpointProtocol(
    candidates=tuple(RoundNumber(value) for value in (25, 50, 75, 100, 125, 150, 200)), maximum_round=RoundNumber(200)
)
# Prospective research amendment completing Journal §13.2: primary = declared maximum round.
CHECKPOINT_SELECTION_RULE = CheckpointSelectionRule.FIXED_TERMINAL_MAXIMUM_ROUND
FEDAVG_LOCAL_EPOCHS = LocalEpochCount(1)
FEDPROX_COEFFICIENTS = tuple(ProximalCoefficient(value) for value in (0.001, 0.01, 0.1, 1.0))
DITTO_RETAINED_EFFECT_MINIMUM = Ratio(0.75)
DITTO_PARTIAL_EFFECT_MINIMUM = Ratio(0.25)
DITTO_ALTERNATIVE_ROUTE_DIFFERENCE = MetricValue(0.05)
NBAIOT_AUTOENCODER = AutoencoderProtocol(widths=(115, 86, 58, 38, 29, 38, 58, 86, 115))
WEIGHT_DECAY = WeightDecay(0.0)
OPTIMIZER = OptimizerProtocol(identity=OptimizerId.ADAM, weight_decay=WEIGHT_DECAY)
LEARNING_RATE = LearningRate(0.001)
BATCH_SIZE = BatchSize(256)
# CUDA-resident TensorDataset loaders cannot fork worker processes.
CENTRALIZED_DATALOADER_WORKER_COUNT = DataLoaderWorkerCount(0)
DITTO_REGULARIZATION_GRID = tuple(DittoRegularization(value) for value in (0.05, 0.1, 0.2))
DITTO_PRIMARY_REGULARIZATION = DittoRegularization(0.1)
CENTRALIZED_TRAINING_PROTOCOL = CentralizedTrainingProtocol(
    kind=CentralizedModelId.CENTRALIZED_AUTOENCODER,
    optimizer=OPTIMIZER,
)
FEDAVG_TRAINING_PROTOCOL = FedAvgProtocol(
    kind=TrainingModelId.FEDAVG_AUTOENCODER,
    local_epochs=FEDAVG_LOCAL_EPOCHS,
    optimizer=OPTIMIZER,
)
FEDPROX_TRAINING_PROTOCOLS = tuple(
    FedProxProtocol(
        kind=TrainingModelId.FEDPROX_AUTOENCODER,
        local_epochs=FEDAVG_LOCAL_EPOCHS,
        optimizer=OPTIMIZER,
        coefficient=coefficient,
    )
    for coefficient in FEDPROX_COEFFICIENTS
)
DITTO_TRAINING_PROTOCOLS = tuple(
    DittoProtocol(
        kind=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
        regularization=regularization,
    )
    for regularization in DITTO_REGULARIZATION_GRID
)
