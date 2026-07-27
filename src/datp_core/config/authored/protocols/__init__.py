"""Authored protocol configuration document (protocols.yaml), composed from the focused
per-responsibility protocol submodules."""

from __future__ import annotations

from pydantic import model_validator

from datp_core.config.authored.base import SchemaVersionOneConfigModel, StrictFrozenConfigModel
from datp_core.config.authored.protocols.evaluation import (
    EligibilityFallbackConfig,
    EligibilityPolicyConfig,
    EvaluationResultContractConfig,
    NestedReplicatePolicyConfig,
    ResultTypeConfig,
)
from datp_core.config.authored.protocols.operations import (
    BenignDecisionRateConfig,
    CheckpointStorageConfig,
    ClusterDiagnosticsConfig,
    CommunicationEstimationContractConfig,
    CrossClientAggregationConfig,
    FieldEncodingConfig,
    HeterogeneityDiagnosticsConfig,
    JsDivergenceConfig,
    MetricDefinitionsConfig,
    MetricFormulaConfig,
    ModelExchangeConfig,
    OperationalInputsConfig,
    PrecisionPolicyConfig,
    ThresholdEstimationMetricsConfig,
    ThresholdExchangeConfig,
    ThresholdExchangeEntryConfig,
)
from datp_core.config.authored.protocols.reporting import ReportColumnConfig, ReportDefaultsConfig, ReportProfileConfig
from datp_core.config.authored.protocols.statistics import StatisticalProfileConfig
from datp_core.config.authored.protocols.thresholds import (
    BaseThresholdPolicyConfig,
    CalibrationFallbackPolicyConfig,
    CentralizedPooledThresholdPolicyConfig,
    ClusterThresholdPolicyConfig,
    FamilyMeanThresholdPolicyConfig,
    FederatedFixedCoefficientPolicyConfig,
    FederatedMatchedExceedancePolicyConfig,
    LocalGlobalShrinkagePolicyConfig,
    LocalQuantileThresholdPolicyConfig,
    SharedMeanThresholdPolicyConfig,
    SharedPooledThresholdPolicyConfig,
    SharedWeightedThresholdPolicyConfig,
    SplitConformalThresholdPolicyConfig,
    TypedThresholdPolicyConfig,
)
from datp_core.config.authored.protocols.training import (
    BatchingProfileConfig,
    CheckpointProfileConfig,
    DeterminismProfileConfig,
    FederationStrategyConfig,
    ModelArchitectureConfig,
    NormalizationStrategyConfig,
    OptimizerProfileConfig,
    SeedCohortConfig,
    TrainingProfileConfig,
)
from datp_core.config.domain_models import NormalizationFitScopes


class MetricBundleConfig(StrictFrozenConfigModel):
    metrics: list[str]
    cross_client_aggregation: str | None = None
    primary_dispersion_metric: str | None = None
    model_quality_control: str | None = None
    excludes_ineligible_clients: bool | None = None
    requires_attack_evaluable_clients: bool | None = None


class AuthoredProtocolsConfig(SchemaVersionOneConfigModel):
    model_architectures: dict[str, ModelArchitectureConfig]
    optimizers: dict[str, OptimizerProfileConfig]
    batching: dict[str, BatchingProfileConfig]
    determinism: DeterminismProfileConfig
    seed_cohorts: dict[str, SeedCohortConfig]
    checkpoint_profiles: dict[str, CheckpointProfileConfig]
    training_profiles: dict[str, TrainingProfileConfig]
    eligibility_policies: dict[str, EligibilityPolicyConfig]
    normalization_strategies: dict[str, NormalizationStrategyConfig]
    normalization_fit_scopes: NormalizationFitScopes
    normalization_leakage_rule: str
    threshold_policies: dict[str, TypedThresholdPolicyConfig]
    metric_definitions: MetricDefinitionsConfig
    metric_bundles: dict[str, MetricBundleConfig]
    nested_replicate_policy: NestedReplicatePolicyConfig
    result_types: dict[str, ResultTypeConfig]
    evaluation_result_contract: EvaluationResultContractConfig
    communication_estimation_contract: CommunicationEstimationContractConfig
    report_defaults: ReportDefaultsConfig
    operational_inputs: OperationalInputsConfig
    statistical_profiles: dict[str, StatisticalProfileConfig]
    report_profiles: dict[str, ReportProfileConfig]
    communication_estimation: dict[str, object] | None = None

    @model_validator(mode="after")
    def reject_retired_policy_identifiers(self) -> AuthoredProtocolsConfig:
        retired = {"b5", "b3lgs"}
        for identifier in self.threshold_policies:
            normalized = identifier.lower().replace("-", "").replace("_", "")
            if normalized in retired:
                raise ValueError(f"Retired threshold policy identifier is forbidden: {identifier}")
        return self


__all__ = [
    "AuthoredProtocolsConfig",
    "BaseThresholdPolicyConfig",
    "BatchingProfileConfig",
    "BenignDecisionRateConfig",
    "CalibrationFallbackPolicyConfig",
    "CentralizedPooledThresholdPolicyConfig",
    "CheckpointProfileConfig",
    "CheckpointStorageConfig",
    "ClusterDiagnosticsConfig",
    "ClusterThresholdPolicyConfig",
    "CommunicationEstimationContractConfig",
    "CrossClientAggregationConfig",
    "DeterminismProfileConfig",
    "EligibilityFallbackConfig",
    "EligibilityPolicyConfig",
    "EvaluationResultContractConfig",
    "FamilyMeanThresholdPolicyConfig",
    "FederatedFixedCoefficientPolicyConfig",
    "FederatedMatchedExceedancePolicyConfig",
    "FederationStrategyConfig",
    "FieldEncodingConfig",
    "HeterogeneityDiagnosticsConfig",
    "JsDivergenceConfig",
    "LocalGlobalShrinkagePolicyConfig",
    "LocalQuantileThresholdPolicyConfig",
    "MetricBundleConfig",
    "MetricDefinitionsConfig",
    "MetricFormulaConfig",
    "ModelArchitectureConfig",
    "ModelExchangeConfig",
    "NestedReplicatePolicyConfig",
    "NormalizationStrategyConfig",
    "OperationalInputsConfig",
    "OptimizerProfileConfig",
    "PrecisionPolicyConfig",
    "ReportColumnConfig",
    "ReportDefaultsConfig",
    "ReportProfileConfig",
    "ResultTypeConfig",
    "SeedCohortConfig",
    "SharedMeanThresholdPolicyConfig",
    "SharedPooledThresholdPolicyConfig",
    "SharedWeightedThresholdPolicyConfig",
    "SplitConformalThresholdPolicyConfig",
    "StatisticalProfileConfig",
    "ThresholdEstimationMetricsConfig",
    "ThresholdExchangeConfig",
    "ThresholdExchangeEntryConfig",
    "TrainingProfileConfig",
    "TypedThresholdPolicyConfig",
]
