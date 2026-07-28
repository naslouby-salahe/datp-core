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
from datp_core.data.contracts.eligibility import EligibilityPolicy
from datp_core.data.contracts.enums import DatasetCapability
from datp_core.evaluation.specs import EvaluationResultContract
from datp_core.experiments import ResultTypeRecord


def resolve_eligibility_policies(
    authored: AuthoredProtocolsConfig,
) -> dict[EligibilityPolicyId, EligibilityPolicy]:
    return {
        EligibilityPolicyId(k): EligibilityPolicy(
            identifier=EligibilityPolicyId(k),
            minimum_benign_calibration_count=int(v.minimum_benign_calibration_count),
            require_non_empty_benign_test=(v.fpr_evaluable_requires_non_empty_benign_test_denominator),
            required_attack_capabilities=tuple(DatasetCapability(cap) for cap in v.attack_evaluable_requires),
            exclude_ineligible_clients_from_primary_dispersion=v.ineligible_clients_excluded_from_primary_dispersion,
            zero_eligible_clients_is_blocking=bool(v.zero_eligible_clients_behavior),
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


def resolve_evaluation_result_contract(cfg: EvaluationResultContractConfig) -> EvaluationResultContract:
    return EvaluationResultContract(
        per_evaluation_result_type=cfg.per_evaluation_result_type,
        per_evaluation_eligibility_result_type=cfg.per_evaluation_eligibility_result_type,
        per_evaluation_required_records=tuple(cfg.per_evaluation_required_records),
    )
