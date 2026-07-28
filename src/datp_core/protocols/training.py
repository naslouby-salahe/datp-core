"""Training declarations."""

from datp_core.domain.values import (
    BatchSize,
    DittoRegularization,
    LearningRate,
    LocalEpochCount,
    MetricValue,
    ProximalCoefficient,
    Ratio,
    RoundNumber,
)

from .models import AutoencoderProtocol, CheckpointProtocol, OptimizerProtocol

CHECKPOINT_PROTOCOL = CheckpointProtocol(
    candidates=tuple(RoundNumber(value) for value in (25, 50, 75, 100, 125, 150, 200)), maximum_round=RoundNumber(200)
)
FEDAVG_LOCAL_EPOCHS = LocalEpochCount(1)
FEDPROX_COEFFICIENTS = tuple(ProximalCoefficient(value) for value in (0.001, 0.01, 0.1, 1.0))
DITTO_RETAINED_EFFECT_MINIMUM = Ratio(0.75)
DITTO_PARTIAL_EFFECT_MINIMUM = Ratio(0.25)
DITTO_ALTERNATIVE_ROUTE_DIFFERENCE = MetricValue(0.05)
NBAIOT_AUTOENCODER = AutoencoderProtocol(widths=(115, 86, 58, 38, 29, 38, 58, 86, 115))
OPTIMIZER = OptimizerProtocol(identity="adam")
LEARNING_RATE = LearningRate(0.001)
BATCH_SIZE = BatchSize(256)
DITTO_REGULARIZATION_GRID = tuple(DittoRegularization(value) for value in (0.05, 0.1, 0.2))
DITTO_PRIMARY_REGULARIZATION = DittoRegularization(0.1)
