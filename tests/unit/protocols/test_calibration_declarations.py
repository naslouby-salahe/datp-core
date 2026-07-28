from datp_core.protocols.calibration import CALIBRATION_SIZES, CANONICAL_QUANTILE, QUANTILE_GRID


def test_calibration_grids_are_locked() -> None:
    assert CANONICAL_QUANTILE.value == 0.95
    assert tuple(item.value for item in QUANTILE_GRID) == (0.9, 0.95, 0.975, 0.99)
    assert tuple(item.value for item in CALIBRATION_SIZES) == (50, 100, 250, 500, 1000, 5000)
