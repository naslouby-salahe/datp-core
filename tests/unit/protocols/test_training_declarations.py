from datp_core.domain.enums import OptimizerId
from datp_core.protocols.training import (
    BATCH_SIZE,
    CENTRALIZED_TRAINING_PROTOCOL,
    CHECKPOINT_PROTOCOL,
    DITTO_ALTERNATIVE_ROUTE_DIFFERENCE,
    DITTO_PARTIAL_EFFECT_MINIMUM,
    DITTO_PRIMARY_REGULARIZATION,
    DITTO_REGULARIZATION_GRID,
    DITTO_RETAINED_EFFECT_MINIMUM,
    DITTO_TRAINING_PROTOCOLS,
    FEDAVG_LOCAL_EPOCHS,
    FEDAVG_TRAINING_PROTOCOL,
    FEDPROX_COEFFICIENTS,
    FEDPROX_TRAINING_PROTOCOLS,
    LEARNING_RATE,
    NBAIOT_AUTOENCODER,
    OPTIMIZER,
)


def test_training_grids_are_locked() -> None:
    assert CHECKPOINT_PROTOCOL.maximum_round.value == 200
    assert FEDAVG_LOCAL_EPOCHS.value == 1
    assert tuple(value.value for value in FEDPROX_COEFFICIENTS) == (0.001, 0.01, 0.1, 1)
    assert DITTO_RETAINED_EFFECT_MINIMUM.value == 0.75
    assert DITTO_PARTIAL_EFFECT_MINIMUM.value == 0.25
    assert DITTO_ALTERNATIVE_ROUTE_DIFFERENCE.value == 0.05
    assert NBAIOT_AUTOENCODER.widths == (115, 86, 58, 38, 29, 38, 58, 86, 115)
    assert OPTIMIZER.identity is OptimizerId.ADAM
    assert LEARNING_RATE.value == 0.001
    assert BATCH_SIZE.value == 256
    assert tuple(value.value for value in DITTO_REGULARIZATION_GRID) == (0.05, 0.1, 0.2)
    assert DITTO_PRIMARY_REGULARIZATION.value == 0.1
    assert CENTRALIZED_TRAINING_PROTOCOL.optimizer == OPTIMIZER
    assert FEDAVG_TRAINING_PROTOCOL.local_epochs == FEDAVG_LOCAL_EPOCHS
    assert tuple(item.coefficient for item in FEDPROX_TRAINING_PROTOCOLS) == FEDPROX_COEFFICIENTS
    assert tuple(item.regularization for item in DITTO_TRAINING_PROTOCOLS) == DITTO_REGULARIZATION_GRID
