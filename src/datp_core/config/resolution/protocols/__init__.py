"""Resolution of the authored protocol document (protocols.yaml) into every immutable protocol
record, composed from the focused per-responsibility resolution submodules."""

from __future__ import annotations

from typing import cast

from attrs import define

from datp_core.config.authored.protocols import AuthoredProtocolsConfig
from datp_core.config.operational_contracts import (
    CommunicationEstimationContractRecord,
    OperationalInputsRecord,
)
from datp_core.config.report_profiles import ReportDefaultsRecord, ReportProfileRecord
from datp_core.config.resolution.protocols.evaluation import (
    resolve_eligibility_policies,
    resolve_evaluation_result_contract,
    resolve_nested_replicate_policy,
    resolve_result_type,
)
from datp_core.config.resolution.protocols.operations import (
    resolve_communication_estimation_contract,
    resolve_metric_definitions,
    resolve_operational_inputs,
)
from datp_core.config.resolution.protocols.reporting import resolve_report_defaults, resolve_report_profile
from datp_core.config.resolution.protocols.statistics import resolve_statistical_profiles
from datp_core.config.resolution.protocols.thresholds import (
    resolve_quantile_estimators,
    resolve_threshold_policies,
    resolve_threshold_policy_defaults,
)
from datp_core.config.resolution.protocols.training import (
    ProtocolDeterminismRecord,
    resolve_batching_profiles,
    resolve_checkpoint_profiles,
    resolve_model_architectures,
    resolve_normalization_strategies,
    resolve_optimizers,
    resolve_protocol_determinism,
    resolve_seed_cohorts,
    resolve_training_profiles,
)
from datp_core.config.statistical_profiles import NestedReplicatePolicyRecord, StatisticalProfileRecord
from datp_core.core.identifiers import (
    CheckpointProfileId,
    EligibilityPolicyId,
    MetricBundleId,
    NormalizationStrategyId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.core.immutability import deep_freeze
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.contracts import EligibilityPolicyRecord, NormalizationStrategyRecord
from datp_core.evaluation import (
    EvaluationResultContractRecord,
    MetricBundleRecord,
    MetricDefinitionsRecord,
)
from datp_core.experiments import ResultTypeRecord
from datp_core.learning.contracts.architecture import ModelArchitectureRecord
from datp_core.learning.contracts.checkpoints import CheckpointProfileRecord
from datp_core.learning.contracts.optimization import BatchingRecord, OptimizerRecord
from datp_core.learning.contracts.seeds import SeedCohortRecord
from datp_core.learning.contracts.training import TrainingProfileRecord
from datp_core.thresholding.policies.common import QuantileEstimatorRecord, ThresholdPolicyDefaultsRecord
from datp_core.thresholding.policies.union import ThresholdPolicyRecord


def _resolve_metric_bundles(authored: AuthoredProtocolsConfig) -> dict[MetricBundleId, MetricBundleRecord]:
    return {
        MetricBundleId(k): MetricBundleRecord(
            identifier=MetricBundleId(k),
            metrics=tuple(v.metrics),
            cross_client_aggregation=v.cross_client_aggregation,
            primary_dispersion_metric=v.primary_dispersion_metric,
            model_quality_control=v.model_quality_control,
            excludes_ineligible_clients=v.excludes_ineligible_clients,
            requires_attack_evaluable_clients=v.requires_attack_evaluable_clients,
        )
        for k, v in authored.metric_bundles.items()
    }


@define(frozen=True, slots=True, kw_only=True)
class ResolvedProtocols:
    """Every immutable record resolved from the authored protocol document (protocols.yaml)."""

    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfileRecord]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortRecord]
    statistical_profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]
    threshold_policies: dict[ThresholdPolicyId, ThresholdPolicyRecord]
    model_architectures: TypedDomainRegistry[str, ModelArchitectureRecord]
    optimizers: TypedDomainRegistry[str, OptimizerRecord]
    batching_profiles: TypedDomainRegistry[str, BatchingRecord]
    eligibility_policies: TypedDomainRegistry[EligibilityPolicyId, EligibilityPolicyRecord]
    normalization_strategies: TypedDomainRegistry[NormalizationStrategyId,
        NormalizationStrategyRecord]
    quantile_estimators: TypedDomainRegistry[str, QuantileEstimatorRecord]
    metric_bundles: TypedDomainRegistry[MetricBundleId, MetricBundleRecord]
    report_profiles: TypedDomainRegistry[str, ReportProfileRecord]
    metric_definitions: MetricDefinitionsRecord
    communication_estimation_contract: CommunicationEstimationContractRecord
    operational_inputs: OperationalInputsRecord
    communication_estimation: dict[str, object] | None
    protocol_determinism: ProtocolDeterminismRecord
    normalization_fit_scopes: dict[str, str]
    normalization_leakage_rule: str
    threshold_policy_defaults: ThresholdPolicyDefaultsRecord
    nested_replicate_policy: NestedReplicatePolicyRecord
    result_types: TypedDomainRegistry[str, ResultTypeRecord]
    evaluation_result_contract: EvaluationResultContractRecord
    report_defaults: ReportDefaultsRecord


def resolve_protocols(authored: AuthoredProtocolsConfig) -> ResolvedProtocols:
    """Resolve the authored protocol document (protocols.yaml) into every immutable protocol record."""
    resolved_communication_estimation = (
        cast(dict, deep_freeze(authored.communication_estimation))
        if authored.communication_estimation is not None
        else None
    )
    return ResolvedProtocols(
        training_profiles=TypedDomainRegistry(_items=resolve_training_profiles(authored)),
        checkpoint_profiles=TypedDomainRegistry(_items=resolve_checkpoint_profiles(authored)),
        seed_cohorts=TypedDomainRegistry(_items=resolve_seed_cohorts(authored)),
        statistical_profiles=TypedDomainRegistry(_items=resolve_statistical_profiles(authored)),
        threshold_policies=resolve_threshold_policies(authored),
        model_architectures=TypedDomainRegistry(_items=resolve_model_architectures(authored)),
        optimizers=TypedDomainRegistry(_items=resolve_optimizers(authored)),
        batching_profiles=TypedDomainRegistry(_items=resolve_batching_profiles(authored)),
        eligibility_policies=TypedDomainRegistry(_items=resolve_eligibility_policies(authored)),
        normalization_strategies=TypedDomainRegistry(
            _items=resolve_normalization_strategies(authored)),
        quantile_estimators=TypedDomainRegistry(_items=resolve_quantile_estimators(authored)),
        metric_bundles=TypedDomainRegistry(_items=_resolve_metric_bundles(authored)),
        report_profiles=TypedDomainRegistry(
            _items={key: resolve_report_profile(key, v)
                                                for key, v in authored.report_profiles.items()}
        ),
        metric_definitions=resolve_metric_definitions(authored.metric_definitions),
        communication_estimation_contract=resolve_communication_estimation_contract(
            authored.communication_estimation_contract
        ),
        operational_inputs=resolve_operational_inputs(authored.operational_inputs),
        communication_estimation=resolved_communication_estimation,
        protocol_determinism=resolve_protocol_determinism(authored.determinism),
        normalization_fit_scopes=dict(authored.normalization_fit_scopes),
        normalization_leakage_rule=authored.normalization_leakage_rule,
        threshold_policy_defaults=resolve_threshold_policy_defaults(
            authored.threshold_policy_defaults),
        nested_replicate_policy=resolve_nested_replicate_policy(authored.nested_replicate_policy),
        result_types=TypedDomainRegistry(
            _items={key: resolve_result_type(key, v) for key, v in authored.result_types.items()}
        ),
        evaluation_result_contract=resolve_evaluation_result_contract(
            authored.evaluation_result_contract),
        report_defaults=resolve_report_defaults(authored.report_defaults),
    )
