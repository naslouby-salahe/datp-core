import pytest
from pydantic import ValidationError

from datp_core.domain.enums import CentralizedModelId, CentralizedThresholdMethod
from datp_core.domain.values import Quantile, Ratio
from datp_core.protocols.models import (
    CentralizedQuantileProtocol,
    CentralizedTrainingProtocol,
    OptimizerProtocol,
    TemporalSplitProtocol,
)


def test_models_are_frozen_and_reject_extra_fields() -> None:
    split = TemporalSplitProtocol(
        historical_training=Ratio(0.55),
        historical_calibration=Ratio(0.15),
        future_recalibration=Ratio(0.1),
        future_evaluation=Ratio(0.2),
    )
    with pytest.raises(ValidationError):
        TemporalSplitProtocol.model_validate_json(
            '{"historical_training":{"value":0.55},"historical_calibration":{"value":0.15},'
            '"future_recalibration":{"value":0.1},"future_evaluation":{"value":0.2},"unexpected":true}'
        )
    with pytest.raises(ValidationError):
        TemporalSplitProtocol.model_validate_json(
            '{"historical_training":{"value":"0.55"},"historical_calibration":{"value":0.15},'
            '"future_recalibration":{"value":0.1},"future_evaluation":{"value":0.2}}'
        )
    with pytest.raises(ValidationError):
        split.historical_training = Ratio(0.5)


def test_centralized_declarations_are_distinct_from_federated_ones() -> None:
    training = CentralizedTrainingProtocol(
        kind=CentralizedModelId.CENTRALIZED_AUTOENCODER,
        optimizer=OptimizerProtocol(identity="declared"),
    )
    threshold = CentralizedQuantileProtocol(
        method=CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE,
        quantile=Quantile(0.95),
    )
    assert training.kind is CentralizedModelId.CENTRALIZED_AUTOENCODER
    assert threshold.method is CentralizedThresholdMethod.POOLED_BENIGN_QUANTILE
