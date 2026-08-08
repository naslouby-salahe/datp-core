import pytest
from pydantic import ValidationError

from datp_core.core.numeric import Ratio
from datp_core.protocols.splits import TEMPORAL_SPLIT, FractionalSplitProtocol, TemporalSplitProtocol


def test_temporal_split_is_locked() -> None:
    assert TEMPORAL_SPLIT.model_dump(mode="json") == {
        "historical_training": 0.55,
        "historical_calibration": 0.15,
        "future_recalibration": 0.1,
        "future_evaluation": 0.2,
    }


def test_split_protocols_are_frozen_and_reject_extra_fields() -> None:
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


def test_fractional_split_rejects_totals_outside_the_shared_tolerance() -> None:
    with pytest.raises(ValidationError):
        FractionalSplitProtocol(
            training=Ratio(0.5),
            calibration=Ratio(0.3),
            evaluation=Ratio(0.1),
        )
