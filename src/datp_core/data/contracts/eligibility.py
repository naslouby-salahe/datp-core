"""Eligibility-related contract records."""

from __future__ import annotations

from attrs import define

from datp_core.core.identifiers import EligibilityPolicyId, NormalizationStrategyId
from datp_core.core.numbers import PositiveInt


@define(frozen=True, slots=True, kw_only=True)
class EligibilityFallbackRecord:
    threshold_source: str
    shared_construction: str
    reported_status: str
    enters_primary_dispersion: bool


@define(frozen=True, slots=True, kw_only=True)
class EligibilityPolicyRecord:
    identifier: EligibilityPolicyId
    minimum_benign_calibration_count: PositiveInt
    determined_before_test_evaluation: bool
    identical_across_policies_in_one_comparison: bool
    fpr_evaluable_requires_non_empty_benign_test_denominator: bool
    attack_evaluable_requires: tuple[str, ...]
    ineligible_clients_excluded_from_primary_dispersion: bool
    ineligible_client_deployment_fallback: EligibilityFallbackRecord
    zero_eligible_clients_behavior: str
    affects_standard_eligibility_minimum: bool | None
    permitted_use: str | None


@define(frozen=True, slots=True, kw_only=True)
class NormalizationStrategyRecord:
    identifier: NormalizationStrategyId
    formula: str
    fitted_statistics: tuple[str, ...]
    constant_feature_rule: str
    out_of_range_transform_values: str
    fit_population: str
    standard_deviation_ddof: int | None
