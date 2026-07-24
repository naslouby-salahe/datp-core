"""Authored operational analysis, communication estimation, and metric definition contracts
(protocols.yaml)."""

from __future__ import annotations

from pydantic import ConfigDict

from datp_core.config.authored.base import StrictFrozenConfigModel


class FieldEncodingConfig(StrictFrozenConfigModel):
    bytes_per_field: int
    byte_order: str


class ThresholdExchangeEntryConfig(StrictFrozenConfigModel):
    uplink_fields_per_client: list[str] | None = None
    downlink_fields_per_client: list[str] | None = None
    candidate_grid_downlink_fields_per_client: list[str] | None = None
    candidate_grid_uplink_fields_per_client_per_candidate: list[str] | None = None


class ThresholdExchangeConfig(StrictFrozenConfigModel):
    direction: str
    b1: ThresholdExchangeEntryConfig
    b2: ThresholdExchangeEntryConfig
    b4: ThresholdExchangeEntryConfig
    federated_summary: ThresholdExchangeEntryConfig


class ModelExchangeConfig(StrictFrozenConfigModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, protected_namespaces=())

    field_width: str
    directions: list[str]
    bytes_per_round_formula: str


class CheckpointStorageConfig(StrictFrozenConfigModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, protected_namespaces=())

    contents: list[str]
    model_parameter_bytes_formula: str


class CommunicationEstimationContractConfig(StrictFrozenConfigModel):
    estimate_basis: str
    field_encodings: dict[str, FieldEncodingConfig]
    threshold_exchange: ThresholdExchangeConfig
    candidate_grid_payload: str
    model_exchange: ModelExchangeConfig
    checkpoint_storage: CheckpointStorageConfig
    filename_match_is_not_lineage_evidence: bool
    frozen_artifacts_immutable: bool
    ambiguous_latest_reference: str


class MetricFormulaConfig(StrictFrozenConfigModel):
    """Reusable strict leaf descriptor for a single metric definition (superset of all metric keys)."""

    formula: str | None = None
    unit: str | None = None
    direction: str | None = None
    zero_denominator: str | None = None
    requires: list[str] | None = None
    missing_class_behavior: str | None = None
    requires_both_classes: bool | None = None
    role: str | None = None
    invariance_check: str | None = None
    quantile_estimator: str | None = None
    zero_sum_behavior: str | None = None
    zero_oracle_behavior: str | None = None
    zero_mean_behavior: str | None = None
    denominator_stabilizer: str | None = None
    near_zero_mean_threshold_formula: str | None = None
    near_zero_mean_behavior: str | None = None
    near_zero_mean_threshold_factor: float | None = None
    minimum_client_count: int | None = None
    weighting: str | None = None
    comparison_unit: str | None = None


class CrossClientAggregationConfig(StrictFrozenConfigModel):
    mean_fpr: MetricFormulaConfig
    standard_deviation_ddof: int
    cv_fpr: MetricFormulaConfig
    cv_tpr: MetricFormulaConfig
    iqr_fpr: MetricFormulaConfig
    fpr_range: MetricFormulaConfig
    worst_client_fpr: MetricFormulaConfig
    p10_macro_f1: MetricFormulaConfig
    worst_client_ba: MetricFormulaConfig
    jain_index: MetricFormulaConfig
    gini_coefficient: MetricFormulaConfig


class ThresholdEstimationMetricsConfig(StrictFrozenConfigModel):
    absolute_threshold_error: MetricFormulaConfig
    relative_threshold_error: MetricFormulaConfig
    oracle_definition: str
    target_exceedance: MetricFormulaConfig
    signed_attainment_error: MetricFormulaConfig
    absolute_attainment_error: MetricFormulaConfig
    threshold_dispersion: MetricFormulaConfig
    threshold_variance_across_replicates: MetricFormulaConfig


class JsDivergenceConfig(StrictFrozenConfigModel):
    definition: str
    histogram_bins: int
    binning_range: str
    binning_edges: str
    logarithm_base: int
    empty_bin_handling: str
    pairwise_aggregation: str
    unit: str
    direction: str
    minimum_client_count: int


class HeterogeneityDiagnosticsConfig(StrictFrozenConfigModel):
    pairwise_js_divergence: JsDivergenceConfig


class ClusterDiagnosticsConfig(StrictFrozenConfigModel):
    adjusted_rand_index: MetricFormulaConfig
    within_cluster_dispersion: MetricFormulaConfig
    across_cluster_dispersion: MetricFormulaConfig


class PrecisionPolicyConfig(StrictFrozenConfigModel):
    computation: str
    rounding: str


class MetricDefinitionsConfig(StrictFrozenConfigModel):
    prediction_rule: str
    per_client_before_aggregation: bool
    test_rows_only: bool
    fpr: MetricFormulaConfig
    tpr: MetricFormulaConfig
    balanced_accuracy: MetricFormulaConfig
    macro_f1: MetricFormulaConfig
    auroc: MetricFormulaConfig
    cross_client_aggregation: CrossClientAggregationConfig
    threshold_estimation: ThresholdEstimationMetricsConfig
    heterogeneity_diagnostics: HeterogeneityDiagnosticsConfig
    cluster_diagnostics: ClusterDiagnosticsConfig
    precision_policy: PrecisionPolicyConfig
    metric_statuses: list[str]
    forbidden_substitutions: list[str]


class BenignDecisionRateConfig(StrictFrozenConfigModel):
    configured: bool
    value: float | None = None
    required_fields: list[str]
    finite_value_validation: str
    non_negative_validation: str
    unavailable_behavior: str
    invented_rate_forbidden: bool


class OperationalInputsConfig(StrictFrozenConfigModel):
    benign_decision_rate: BenignDecisionRateConfig
