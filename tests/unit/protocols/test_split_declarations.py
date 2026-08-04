from datp_core.protocols.splits import TEMPORAL_SPLIT


def test_temporal_split_is_locked() -> None:
    assert TEMPORAL_SPLIT.model_dump(mode="json") == {
        "historical_training": 0.55,
        "historical_calibration": 0.15,
        "future_recalibration": 0.1,
        "future_evaluation": 0.2,
    }
