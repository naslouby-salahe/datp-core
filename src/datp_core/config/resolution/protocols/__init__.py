"""Resolution of the authored protocol document (protocols.yaml) into every immutable protocol
record, composed from the focused per-responsibility resolution submodules."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.config.authored.protocols import AuthoredProtocolsConfig
from datp_core.config.domain_models import NormalizationFitScopes
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
from datp_core.config.resolution.protocols.thresholds import resolve_threshold_policies
from datp_core.config.resolution.protocols.training import (
    ProtocolDeterminismRecord,
    resolve_batching_profiles,
    resolve_checkpoint_profiles,
    resolve_learning_data_schemas,
    resolve_model_architectures,
    resolve_normalization_strategies,
    resolve_optimizers,
    resolve_protocol_determinism,
    resolve_runtime_profile,
    resolve_seed_cohorts,
    resolve_seed_derivation_profile,
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
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.contracts.eligibility import EligibilityPolicy
from datp_core.data.contracts.materialization import NormalizationConfig
from datp_core.evaluation.enums import MetricId
from datp_core.evaluation.specs import (
    EvaluationResultContract,
    MetricBundleSpec,
    MetricDefinitions,
)
from datp_core.experiments import ResultTypeRecord
from datp_core.learning.contracts.checkpoints import CheckpointProfile
from datp_core.learning.contracts.model import (
    AdamOptimizerProfile,
    BatchingProfile,
    DenseAutoencoderProfile,
    LearningDataSchema,
)
from datp_core.learning.contracts.training import SeedCohortProfile, TrainingProfile
from datp_core.learning.model.runtime import SeedDerivationProfile, TorchRuntimeProfile
from datp_core.thresholding.policies import ThresholdPolicyRecord


_METRIC_ID_MAP = {
    "fpr": "false_positive_rate",
    "tpr": "true_positive_rate",
    "worst_client_ba": "worst_client_balanced_accuracy",
}

_DEFAULT_CROSS_CLIENT_METRICS = (
    "cv_fpr", "iqr_fpr", "fpr_range", "worst_client_fpr",
    "jain_index", "gini_coefficient", "standard_deviation_fpr",
    "mean_fpr",
)

def _map_metric(name: str) -> MetricId:
    return MetricId(_METRIC_ID_MAP.get(name, name))

def _resolve_metric_bundles(authored: AuthoredProtocolsConfig) -> dict[MetricBundleId, MetricBundleSpec]:
    bundles: dict[MetricBundleId, MetricBundleSpec] = {}
    for k, v in authored.metric_bundles.items():
        metrics = tuple(_map_metric(m) for m in v.metrics)
        cross_client = (
            tuple(_map_metric(m) for m in v.cross_client_aggregation)
            if v.cross_client_aggregation
            else tuple(
                _map_metric(m) for m in _DEFAULT_CROSS_CLIENT_METRICS
                if m in v.metrics
            )
        )
        primary = _map_metric(v.primary_dispersion_metric) if v.primary_dispersion_metric else (
            cross_client[0] if cross_client else _map_metric("cv_fpr")
        )
        qc_default = _map_metric("auroc")
        if v.model_quality_control:
            model_qc = _map_metric(v.model_quality_control)
        elif qc_default in metrics:
            model_qc = qc_default
        else:
            model_qc = metrics[0]
        bundles[MetricBundleId(k)] = MetricBundleSpec(
            identifier=MetricBundleId(k),
            metrics=metrics,
            cross_client_metrics=cross_client,
            primary_dispersion_metric=primary,
            model_quality_control=model_qc,
            excludes_ineligible_clients=v.excludes_ineligible_clients if v.excludes_ineligible_clients is not None else False,
            requires_attack_evaluable_clients=v.requires_attack_evaluable_clients if v.requires_attack_evaluable_clients is not None else False,
        )
    return bundles


class ResolvedProtocols(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    """Every immutable record resolved from the authored protocol document (protocols.yaml)."""

    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfile]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfile]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortProfile]
    statistical_profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]
    threshold_policies: dict[ThresholdPolicyId, ThresholdPolicyRecord]
    model_architectures: TypedDomainRegistry[str, DenseAutoencoderProfile]
    optimizers: TypedDomainRegistry[str, AdamOptimizerProfile]
    batching_profiles: TypedDomainRegistry[str, BatchingProfile]
    eligibility_policies: TypedDomainRegistry[EligibilityPolicyId, EligibilityPolicy]
    normalization_strategies: TypedDomainRegistry[NormalizationStrategyId, NormalizationConfig]
    metric_bundles: TypedDomainRegistry[MetricBundleId, MetricBundleSpec]
    report_profiles: TypedDomainRegistry[str, ReportProfileRecord]
    metric_definitions: MetricDefinitions
    communication_estimation_contract: CommunicationEstimationContractRecord
    operational_inputs: OperationalInputsRecord
    communication_estimation: dict[str, object] | None
    protocol_determinism: ProtocolDeterminismRecord
    normalization_fit_scopes: NormalizationFitScopes
    normalization_leakage_rule: str
    nested_replicate_policy: NestedReplicatePolicyRecord
    result_types: TypedDomainRegistry[str, ResultTypeRecord]
    evaluation_result_contract: EvaluationResultContract
    report_defaults: ReportDefaultsRecord


def resolve_protocols(authored: AuthoredProtocolsConfig) -> ResolvedProtocols:
    """Resolve the authored protocol document (protocols.yaml) into every immutable protocol record."""
    resolved_communication_estimation = (
        dict(authored.communication_estimation) if authored.communication_estimation is not None else None
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
        normalization_strategies=TypedDomainRegistry(_items=resolve_normalization_strategies(authored)),
        metric_bundles=TypedDomainRegistry(_items=_resolve_metric_bundles(authored)),
        report_profiles=TypedDomainRegistry(
            _items={key: resolve_report_profile(key, v) for key, v in authored.report_profiles.items()}
        ),
        metric_definitions=resolve_metric_definitions(authored.metric_definitions),
        communication_estimation_contract=resolve_communication_estimation_contract(
            authored.communication_estimation_contract
        ),
        operational_inputs=resolve_operational_inputs(authored.operational_inputs),
        communication_estimation=resolved_communication_estimation,
        protocol_determinism=resolve_protocol_determinism(authored.determinism),
        normalization_fit_scopes=authored.normalization_fit_scopes,
        normalization_leakage_rule=authored.normalization_leakage_rule,
        nested_replicate_policy=resolve_nested_replicate_policy(authored.nested_replicate_policy),
        result_types=TypedDomainRegistry(
            _items={key: resolve_result_type(key, v) for key, v in authored.result_types.items()}
        ),
        evaluation_result_contract=resolve_evaluation_result_contract(authored.evaluation_result_contract),
        report_defaults=resolve_report_defaults(authored.report_defaults),
    )
