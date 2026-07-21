"""Pure resolved records for the protocol contract blocks with no current downstream consumer.

These blocks (metric definitions, artifact identity, communication estimation, operational
inputs, report profiles) are strictly authored and validated in ``protocols.yaml`` but are not
yet read by any Phase 1 execution path. They are still resolved losslessly into this pure domain
representation -- never dropped -- so every authored field is retained and scientific-identity
relevant blocks participate in the scientific fingerprint.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from attrs import define, field


@define(frozen=True, slots=True, kw_only=True)
class MetricFormulaRecord:
    """Reusable leaf descriptor for a single metric definition (superset of all metric keys)."""

    formula: str | None
    unit: str | None
    direction: str | None
    zero_denominator: str | None
    requires: tuple[str, ...] | None
    missing_class_behavior: str | None
    requires_both_classes: bool | None
    role: str | None
    invariance_check: str | None
    quantile_estimator: str | None
    zero_sum_behavior: str | None
    zero_oracle_behavior: str | None
    zero_mean_behavior: str | None
    denominator_stabilizer: str | None
    near_zero_mean_threshold_formula: str | None
    near_zero_mean_behavior: str | None
    minimum_client_count: int | None
    weighting: str | None
    comparison_unit: str | None


@define(frozen=True, slots=True, kw_only=True)
class CrossClientAggregationRecord:
    mean_fpr: MetricFormulaRecord
    standard_deviation_ddof: int
    cv_fpr: MetricFormulaRecord
    cv_tpr: MetricFormulaRecord
    iqr_fpr: MetricFormulaRecord
    fpr_range: MetricFormulaRecord
    worst_client_fpr: MetricFormulaRecord
    p10_macro_f1: MetricFormulaRecord
    worst_client_ba: MetricFormulaRecord
    jain_index: MetricFormulaRecord
    gini_coefficient: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class ThresholdEstimationMetricsRecord:
    absolute_threshold_error: MetricFormulaRecord
    relative_threshold_error: MetricFormulaRecord
    oracle_definition: str
    target_exceedance: MetricFormulaRecord
    signed_attainment_error: MetricFormulaRecord
    absolute_attainment_error: MetricFormulaRecord
    threshold_dispersion: MetricFormulaRecord
    threshold_variance_across_replicates: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class JsDivergenceRecord:
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


@define(frozen=True, slots=True, kw_only=True)
class HeterogeneityDiagnosticsRecord:
    pairwise_js_divergence: JsDivergenceRecord


@define(frozen=True, slots=True, kw_only=True)
class ClusterDiagnosticsRecord:
    adjusted_rand_index: MetricFormulaRecord
    within_cluster_dispersion: MetricFormulaRecord
    across_cluster_dispersion: MetricFormulaRecord


@define(frozen=True, slots=True, kw_only=True)
class PrecisionPolicyRecord:
    computation: str
    rounding: str


@define(frozen=True, slots=True, kw_only=True)
class MetricDefinitionsRecord:
    prediction_rule: str
    per_client_before_aggregation: bool
    test_rows_only: bool
    fpr: MetricFormulaRecord
    tpr: MetricFormulaRecord
    balanced_accuracy: MetricFormulaRecord
    macro_f1: MetricFormulaRecord
    auroc: MetricFormulaRecord
    cross_client_aggregation: CrossClientAggregationRecord
    threshold_estimation: ThresholdEstimationMetricsRecord
    heterogeneity_diagnostics: HeterogeneityDiagnosticsRecord
    cluster_diagnostics: ClusterDiagnosticsRecord
    precision_policy: PrecisionPolicyRecord
    metric_statuses: tuple[str, ...]
    forbidden_substitutions: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ArtifactFingerprintsRecord:
    source: tuple[str, ...]
    schema_stage: tuple[str, ...]
    materialization: tuple[str, ...]
    client_assignment: tuple[str, ...]
    model_stage: tuple[str, ...]
    training: tuple[str, ...]
    checkpoint: tuple[str, ...]
    score: tuple[str, ...]
    threshold: tuple[str, ...]
    metric: tuple[str, ...]
    analysis: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ArtifactIdentityRecord:
    hash_function: str
    digest_bytes: int
    canonical_serialization: str
    absolute_paths_excluded_from_identity: bool
    fingerprints: ArtifactFingerprintsRecord
    lineage_validation_before_reuse: tuple[str, ...]
    reuse_rejected_when_any_changes: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class FieldEncodingRecord:
    bytes_per_field: int
    byte_order: str


@define(frozen=True, slots=True, kw_only=True)
class ThresholdExchangeEntryRecord:
    uplink_fields_per_client: tuple[str, ...] | None
    downlink_fields_per_client: tuple[str, ...] | None
    candidate_grid_downlink_fields_per_client: tuple[str, ...] | None
    candidate_grid_uplink_fields_per_client_per_candidate: tuple[str, ...] | None


@define(frozen=True, slots=True, kw_only=True)
class ThresholdExchangeRecord:
    direction: str
    b1: ThresholdExchangeEntryRecord
    b2: ThresholdExchangeEntryRecord
    b4: ThresholdExchangeEntryRecord
    federated_summary: ThresholdExchangeEntryRecord


@define(frozen=True, slots=True, kw_only=True)
class ModelExchangeRecord:
    field_width: str
    directions: tuple[str, ...]
    bytes_per_round_formula: str


@define(frozen=True, slots=True, kw_only=True)
class CheckpointStorageRecord:
    contents: tuple[str, ...]
    model_parameter_bytes_formula: str


@define(frozen=True, slots=True, kw_only=True)
class CommunicationEstimationContractRecord:
    estimate_basis: str
    field_encodings: Mapping[str, FieldEncodingRecord]
    threshold_exchange: ThresholdExchangeRecord
    candidate_grid_payload: str
    model_exchange: ModelExchangeRecord
    checkpoint_storage: CheckpointStorageRecord
    filename_match_is_not_lineage_evidence: bool
    frozen_artifacts_immutable: bool
    ambiguous_latest_reference: str


@define(frozen=True, slots=True, kw_only=True)
class BenignDecisionRateRecord:
    configured: bool
    value: float | None
    required_fields: tuple[str, ...]
    finite_value_validation: str
    non_negative_validation: str
    unavailable_behavior: str
    invented_rate_forbidden: bool


@define(frozen=True, slots=True, kw_only=True)
class OperationalInputsRecord:
    benign_decision_rate: BenignDecisionRateRecord


@define(frozen=True, slots=True, kw_only=True)
class ReportColumnRecord:
    name: str
    unit: str
    direction: str


def _as_optional_report_columns(value: object) -> tuple[ReportColumnRecord, ...] | None:
    if value is None:
        return None
    return cast("tuple[ReportColumnRecord, ...]", tuple(cast("list[ReportColumnRecord]", value)))


@define(frozen=True, slots=True, kw_only=True)
class ReportProfileRecord:
    identifier: str
    artifact_type: str
    table_type: str | None
    figure_type: str | None
    estimate_basis: str | None
    columns: tuple[ReportColumnRecord, ...] | None = field(converter=_as_optional_report_columns)
    series: tuple[ReportColumnRecord, ...] | None = field(converter=_as_optional_report_columns)


@define(frozen=True, slots=True, kw_only=True)
class SeedNamespaceRecord:
    key: str
    components: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ProtocolDeterminismRecord:
    """Protocols.yaml's own seed/determinism contract (distinct from runtime.yaml's execution determinism)."""

    seed_domains: tuple[str, ...]
    partition_seed_independent_of_training_seeds: bool
    checkpoint_selection_uses_no_stochastic_seed: bool
    derived_seed_algorithm: Mapping[str, str | int]
    seed_namespaces: Mapping[str, SeedNamespaceRecord]
    resolved_seeds_required_in_manifests: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ThresholdPolicyDefaultsRecord:
    source_score_population: str
    eligibility_filter: str
    attack_rows_forbidden_in_calibration: bool
    non_finite_calibration_score: str
    empty_client_calibration: str
    application_scope: str
    required_diagnostic_fields: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class NestedReplicatePolicyRecord:
    replicate_values_computed_first: bool
    summarized_within_seed_before_across_seed_inference: bool
    seed_level_statistic: str
    replicates_counted_as_independent_units: bool
    additional_required_replicate_statistic: str


@define(frozen=True, slots=True, kw_only=True)
class ResultTypeRecord:
    identifier: str
    permitted_evidence_roles: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class EvaluationResultContractRecord:
    per_evaluation_result_type: str
    per_evaluation_eligibility_result_type: str
    per_evaluation_required_records: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ReportDefaultsRecord:
    ordering: str
    missing_value_policy: str
    table_output_formats: tuple[str, ...]
    figure_output_formats: tuple[str, ...]
    provenance_required_per_artifact: bool
    analysis_defined_direction_token: str
