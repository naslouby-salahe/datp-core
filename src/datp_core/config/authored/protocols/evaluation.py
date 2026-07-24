"""Authored client-eligibility and evaluation result contracts (protocols.yaml)."""

from __future__ import annotations

from datp_core.config.authored.base import StrictFrozenConfigModel


class EligibilityFallbackConfig(StrictFrozenConfigModel):
    threshold_source: str
    shared_construction: str
    reported_status: str
    enters_primary_dispersion: bool


class EligibilityPolicyConfig(StrictFrozenConfigModel):
    minimum_benign_calibration_count: int
    determined_before_test_evaluation: bool
    identical_across_policies_in_one_comparison: bool
    fpr_evaluable_requires_non_empty_benign_test_denominator: bool
    attack_evaluable_requires: list[str]
    ineligible_clients_excluded_from_primary_dispersion: bool
    ineligible_client_deployment_fallback: EligibilityFallbackConfig
    zero_eligible_clients_behavior: str
    affects_standard_eligibility_minimum: bool | None = None
    permitted_use: str | None = None


class NestedReplicatePolicyConfig(StrictFrozenConfigModel):
    replicate_values_computed_first: bool
    summarized_within_seed_before_across_seed_inference: bool
    seed_level_statistic: str
    replicates_counted_as_independent_units: bool
    additional_required_replicate_statistic: str


class ResultTypeConfig(StrictFrozenConfigModel):
    permitted_evidence_roles: list[str]


class EvaluationResultContractConfig(StrictFrozenConfigModel):
    per_evaluation_result_type: str
    per_evaluation_eligibility_result_type: str
    per_evaluation_required_records: list[str]
