"""Split-conformal threshold policy record."""

from __future__ import annotations

from typing import Literal

from attrs import define, field

from datp_core.thresholding.policies.common import _as_tuple_str
from datp_core.thresholding.policies.enums import ThresholdOwnership


@define(frozen=True, slots=True, kw_only=True)
class SplitConformalThresholdPolicyRecord:
    policy: Literal["conformal_local_threshold"]
    conformal_mode: str
    coverage_alpha: float
    nominal_coverage: float
    target_exceedance: float
    rank_formula: str
    order_statistic_selection: str
    interpolation: str
    tie_break: str
    finite_sample_attainability_rule: str
    unattainable_behavior: str
    minimum_sample_count: int
    calibration_unit: str
    calibration_scope: str
    evaluation_unit: str
    coverage_breakdown: tuple[str, ...] = field(converter=_as_tuple_str)
    coverage_target_error: str
    output_type: str
    exchangeability_limitation: str
    unavailable_behavior: str
    threshold_ownership: ThresholdOwnership = field(converter=ThresholdOwnership)
