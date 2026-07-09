"""Split/partition semantics shared by every dataset contract."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SplitType(StrEnum):
    CHRONOLOGICAL_GAPPED = "chronological_gapped"
    RANDOM_SHUFFLE_SEQUENTIAL = "random_shuffle_sequential"
    CHRONOLOGICAL_70_30 = "chronological_70_30"
    FEASIBILITY_PENDING = "feasibility_pending"


class SplitRole(StrEnum):
    TRAIN = "train"
    CALIBRATION_GAP = "calibration_gap"
    CALIBRATION = "calibration"
    TEST_GAP = "test_gap"
    TEST = "test"


CALIBRATION_MIN_ELIGIBLE_ROWS = 100
"""n_min; clients below this fall back to tau_global (Calibration-Pending)."""

CHRONOLOGICAL_GAP_FRACTION = 0.01
"""Locked buffer between adjacent chronological partitions (docs/protocol/artifact_contracts.md #1.1)."""


@dataclass(frozen=True)
class SplitRatios:
    train: float
    calibration: float
    test: float
    train_calibration_gap: float = 0.0
    calibration_test_gap: float = 0.0

    def __post_init__(self) -> None:
        total = self.train + self.calibration + self.test + self.train_calibration_gap + self.calibration_test_gap
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"split ratios must sum to 1.0, got {total}")


def is_calibration_eligible(benign_calibration_row_count: int) -> bool:
    return benign_calibration_row_count >= CALIBRATION_MIN_ELIGIBLE_ROWS
