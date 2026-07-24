"""Resolution of client-eligibility and evaluation-result-contract records."""

from __future__ import annotations

from datp_core.config.authored.protocols import AuthoredProtocolsConfig
from datp_core.config.authored.protocols.evaluation import (
    EvaluationResultContractConfig,
    NestedReplicatePolicyConfig,
    ResultTypeConfig,
)
from datp_core.config.statistical_profiles import NestedReplicatePolicyRecord
from datp_core.core.identifiers import EligibilityPolicyId
from datp_core.core.numbers import PositiveInt
from datp_core.data.contracts import EligibilityFallbackRecord, EligibilityPolicyRecord
from datp_core.evaluation.definitions import EvaluationResultContractRecord
from datp_core.experiments import ResultTypeRecord


def resolve_eligibility_policies(
    authored: AuthoredProtocolsConfig,
) -> dict[EligibilityPolicyId, EligibilityPolicyRecord]:
    return {
        EligibilityPolicyId(k): EligibilityPolicyRecord(
            identifier=EligibilityPolicyId(k),
            minimum_benign_calibration_count=PositiveInt(v.minimum_benign_calibration_count),
            determined_before_test_evaluation=v.determined_before_test_evaluation,
            identical_across_policies_in_one_comparison=v.identical_across_policies_in_one_comparison,
            fpr_evaluable_requires_non_empty_benign_test_denominator=(
                v.fpr_evaluable_requires_non_empty_benign_test_denominator
            ),
            attack_evaluable_requires=tuple(v.attack_evaluable_requires),
            ineligible_clients_excluded_from_primary_dispersion=v.ineligible_clients_excluded_from_primary_dispersion,
            ineligible_client_deployment_fallback=EligibilityFallbackRecord(
                threshold_source=v.ineligible_client_deployment_fallback.threshold_source,
                shared_construction=v.ineligible_client_deployment_fallback.shared_construction,
                reported_status=v.ineligible_client_deployment_fallback.reported_status,
                enters_primary_dispersion=v.ineligible_client_deployment_fallback.enters_primary_dispersion,
            ),
            zero_eligible_clients_behavior=v.zero_eligible_clients_behavior,
            affects_standard_eligibility_minimum=v.affects_standard_eligibility_minimum,
            permitted_use=v.permitted_use,
        )
        for k, v in authored.eligibility_policies.items()
    }


def resolve_nested_replicate_policy(cfg: NestedReplicatePolicyConfig) -> NestedReplicatePolicyRecord:
    return NestedReplicatePolicyRecord(
        replicate_values_computed_first=cfg.replicate_values_computed_first,
        summarized_within_seed_before_across_seed_inference=cfg.summarized_within_seed_before_across_seed_inference,
        seed_level_statistic=cfg.seed_level_statistic,
        replicates_counted_as_independent_units=cfg.replicates_counted_as_independent_units,
        additional_required_replicate_statistic=cfg.additional_required_replicate_statistic,
    )


def resolve_result_type(identifier: str, cfg: ResultTypeConfig) -> ResultTypeRecord:
    return ResultTypeRecord(identifier=identifier, permitted_evidence_roles=tuple(cfg.permitted_evidence_roles))


def resolve_evaluation_result_contract(cfg: EvaluationResultContractConfig) -> EvaluationResultContractRecord:
    return EvaluationResultContractRecord(
        per_evaluation_result_type=cfg.per_evaluation_result_type,
        per_evaluation_eligibility_result_type=cfg.per_evaluation_eligibility_result_type,
        per_evaluation_required_records=tuple(cfg.per_evaluation_required_records),
    )
