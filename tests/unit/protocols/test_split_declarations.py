from datp_core.protocols.splits import TEMPORAL_SPLIT


def test_temporal_split_is_locked() -> None:
    assert TEMPORAL_SPLIT.model_dump(mode="json") == {
        "historical_training": {"value": 0.55},
        "historical_calibration": {"value": 0.15},
        "future_recalibration": {"value": 0.1},
        "future_evaluation": {"value": 0.2},
    }
