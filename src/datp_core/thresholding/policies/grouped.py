"""Family-mean threshold policy record."""

from __future__ import annotations

from typing import Literal

from attrs import define, field

from datp_core.thresholding.policies.enums import ThresholdOwnership


@define(frozen=True, slots=True, kw_only=True)
class FamilyMeanThresholdPolicyRecord:
    policy: Literal["family_threshold"]
    quantile: float
    quantile_estimator: str
    requires_capability: str
    taxonomy_source: str
    aggregated_quantity: str
    aggregation_scope: str
    aggregation_formula: str
    sample_weighting: str
    client_accumulation_order: str
    singleton_family_behavior: str
    family_with_no_eligible_member_behavior: str
    client_without_family_label_behavior: str
    unavailable_without_taxonomy: str
    threshold_ownership: ThresholdOwnership = field(converter=ThresholdOwnership)
