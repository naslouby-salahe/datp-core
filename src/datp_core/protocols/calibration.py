"""Benign-only calibration declarations."""

from datp_core.domain.errors import UnresolvedScientificValueError
from datp_core.domain.values import (
    CalibrationSize,
    CoverageTarget,
    Quantile,
    Ratio,
    ShrinkageWeight,
    SummaryCoefficient,
)

CANONICAL_QUANTILE = Quantile(0.95)
QUANTILE_GRID = tuple(Quantile(value) for value in (0.90, 0.95, 0.975, 0.99))
MINIMUM_BENIGN_SUPPORT = CalibrationSize(100)
CALIBRATION_SIZES = tuple(CalibrationSize(value) for value in (50, 100, 250, 500, 1000, 5000))
FIXED_SHRINKAGE_WEIGHTS = tuple(ShrinkageWeight(value) for value in (0, 0.25, 0.5, 0.75, 1))
CONFORMAL_COVERAGE = CoverageTarget(0.95)
CONFORMAL_SIGNIFICANCE = Ratio(0.05)
SUMMARY_COEFFICIENTS = tuple(SummaryCoefficient(value) for value in (2, 2.5, 3))


def require_group_assignment_input() -> object:
    raise UnresolvedScientificValueError(
        "Grouped threshold assignment input is unresolved", subject="grouped threshold"
    )
