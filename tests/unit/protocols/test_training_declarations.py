import json

import pytest

from datp_core.domain.enums import CentralizedModelId, CentralizedThresholdMethod, OptimizerId, TrainingModelId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import FeatureCount
from datp_core.domain.values.ratios import DittoRegularization, ModelCoefficientValue, Quantile
from datp_core.protocols.calibration import CentralizedQuantileProtocol
from datp_core.protocols.training import (
    BATCH_SIZE,
    CENTRALIZED_TRAINING_PROTOCOL,
    CHECKPOINT_PROTOCOL,
    CICIOT2023_AUTOENCODER,
    DITTO_ALTERNATIVE_ROUTE_DIFFERENCE,
    DITTO_PARTIAL_EFFECT_MINIMUM,
    DITTO_PRIMARY_REGULARIZATION,
    DITTO_REGULARIZATION_GRID,
    DITTO_RETAINED_EFFECT_MINIMUM,
    DITTO_TRAINING_PROTOCOLS,
    EDGE_IIOTSET_NUMERIC_AUTOENCODER,
    FEDAVG_LOCAL_EPOCHS,
    FEDAVG_TRAINING_PROTOCOL,
    FEDPROX_COEFFICIENTS,
    FEDPROX_TRAINING_PROTOCOLS,
    LEARNING_RATE,
    MODEL_ABSORPTION_DECISION_PROTOCOL,
    NBAIOT_AUTOENCODER,
    OPTIMIZER,
    resolve_single_model_federated_training_protocol,
)


def _width_values(protocol) -> tuple[int, ...]:
    return tuple(width.value for width in protocol.widths)


def test_training_grids_are_locked() -> None:
    assert CHECKPOINT_PROTOCOL.maximum_round.value == 200
    assert FEDAVG_LOCAL_EPOCHS.value == 1
    assert tuple(value.value for value in FEDPROX_COEFFICIENTS) == (0.001, 0.01, 0.1, 1)
    assert DITTO_RETAINED_EFFECT_MINIMUM.value == 0.75
    assert DITTO_PARTIAL_EFFECT_MINIMUM.value == 0.25
    assert DITTO_ALTERNATIVE_ROUTE_DIFFERENCE.value == 0.05
    assert MODEL_ABSORPTION_DECISION_PROTOCOL.full_retention_minimum == DITTO_RETAINED_EFFECT_MINIMUM
    assert MODEL_ABSORPTION_DECISION_PROTOCOL.partial_retention_minimum == DITTO_PARTIAL_EFFECT_MINIMUM
    assert _width_values(NBAIOT_AUTOENCODER) == (115, 86, 58, 38, 29, 38, 58, 86, 115)
    assert _width_values(EDGE_IIOTSET_NUMERIC_AUTOENCODER) == (33, 25, 17, 11, 8, 11, 17, 25, 33)
    assert _width_values(CICIOT2023_AUTOENCODER) == (39, 29, 20, 13, 10, 13, 20, 29, 39)
    assert all(isinstance(width, FeatureCount) for width in NBAIOT_AUTOENCODER.widths)
    assert OPTIMIZER.identity is OptimizerId.ADAM
    assert LEARNING_RATE.value == 0.001
    assert BATCH_SIZE.value == 256
    assert tuple(value.value for value in DITTO_REGULARIZATION_GRID) == (0.05, 0.1, 0.2)
    assert DITTO_PRIMARY_REGULARIZATION.value == 0.1
    assert CENTRALIZED_TRAINING_PROTOCOL.optimizer == OPTIMIZER
    assert FEDAVG_TRAINING_PROTOCOL.local_epochs == FEDAVG_LOCAL_EPOCHS
    assert tuple(item.coefficient for item in FEDPROX_TRAINING_PROTOCOLS) == FEDPROX_COEFFICIENTS
    assert tuple(item.regularization for item in DITTO_TRAINING_PROTOCOLS) == DITTO_REGULARIZATION_GRID


def test_autoencoder_width_serialization_remains_scalar() -> None:
    payload = json.loads(NBAIOT_AUTOENCODER.model_dump_json())
    assert payload["widths"] == [115, 86, 58, 38, 29, 38, 58, 86, 115]


def test_single_model_federated_protocol_resolution_is_authoritative() -> None:
    assert (
        resolve_single_model_federated_training_protocol(
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            coefficient=None,
        )
        is FEDAVG_TRAINING_PROTOCOL
    )
    for protocol in FEDPROX_TRAINING_PROTOCOLS:
        assert (
            resolve_single_model_federated_training_protocol(
                model=TrainingModelId.FEDPROX_AUTOENCODER,
                coefficient=ModelCoefficientValue(protocol.coefficient.value),
            )
            is protocol
        )


def test_centralized_declarations_are_distinct_from_federated_ones() -> None:
    training = CENTRALIZED_TRAINING_PROTOCOL
    threshold = CentralizedQuantileProtocol(
        method=CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE,
        quantile=Quantile(0.95),
    )
    assert training.kind is CentralizedModelId.CENTRALIZED_AUTOENCODER
    assert threshold.method is CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE


def test_single_model_federated_protocol_resolution_rejects_invalid_shapes() -> None:
    with pytest.raises(ScientificContractError, match="must not declare"):
        resolve_single_model_federated_training_protocol(
            model=TrainingModelId.FEDAVG_AUTOENCODER,
            coefficient=ModelCoefficientValue(0.1),
        )
    with pytest.raises(ScientificContractError, match="proximal coefficient"):
        resolve_single_model_federated_training_protocol(
            model=TrainingModelId.FEDPROX_AUTOENCODER,
            coefficient=DittoRegularization(0.1),
        )
    with pytest.raises(ScientificContractError, match="global and personalized"):
        resolve_single_model_federated_training_protocol(
            model=TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER,
            coefficient=DittoRegularization(0.1),
        )
