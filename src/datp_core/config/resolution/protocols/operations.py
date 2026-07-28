"""Resolution of operational analysis, communication estimation, and metric definition records."""

from __future__ import annotations

from datp_core.config.authored.protocols.operations import (
    CommunicationEstimationContractConfig,
    MetricDefinitionsConfig,
    MetricFormulaConfig,
    OperationalInputsConfig,
    ThresholdExchangeEntryConfig,
)
from datp_core.config.operational_contracts import (
    BenignDecisionRateRecord,
    CheckpointStorageRecord,
    CommunicationEstimationContractRecord,
    FieldEncodingRecord,
    ModelExchangeRecord,
    OperationalInputsRecord,
    ThresholdExchangeEntryRecord,
    ThresholdExchangeRecord,
)
from datp_core.evaluation.enums import (
    AggregationKind,
    EmptyBinPolicy,
    HistogramEdgeMode,
    HistogramRangeMode,
    MetricDirection,
    MetricId,
    MetricRole,
    MetricUnit,
    MetricStatus,
    MissingClassPolicy,
    PairwiseAggregationMode,
    PrecisionComputation,
    PredictionRule,
    QuantileEstimator,
    RoundingMode,
    WeightingMode,
    ZeroDenominatorPolicy,
)

_EVAL_VALUE_MAP = {
    "undefined_zero_denominator": "unavailable",
    "missing_class_unavailable": "unavailable",
    "unavailable_missing_attack_class": "report_missing_attack_class",
    "none": "unweighted",
    "retain_numerical_value_with_undefined_near_zero_denominator_warning_status": "retain_with_warning",
    "undefined_near_zero_denominator": "unavailable",
    "predicted_attack when score > threshold, otherwise predicted_benign": "score > threshold",
    "standard": "linear_interpolated_order_statistic",
    "ignore": "zero_probability",
    "arithmetic_mean_over_all_available_and_eligible_client_pairs": "mean_unordered_pairs",
    "arithmetic_mean_over_all_unordered_eligible_client_pairs": "mean_unordered_pairs",
    "full_available_precision": "float64",
    "presentation_only": "none",
    "fpr": "false_positive_rate",
    "tpr": "true_positive_rate",
    "worst_client_ba": "worst_client_balanced_accuracy",
    "auto": "pooled_min_max",
    "shared_across_clients": "shared_across_clients",
}

def _map_metric_name(name: str) -> MetricId:
    return MetricId(_EVAL_VALUE_MAP.get(name, name))

def _safe_eval_enum(enum_cls: type, value: str | None) -> object | None:
    if value is None:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        mapped = _EVAL_VALUE_MAP.get(value, value)
        return enum_cls(mapped)


def _safe_denom(value: str | None) -> ZeroDenominatorPolicy | None:
    if value is None:
        return None
    try:
        return ZeroDenominatorPolicy(value)
    except ValueError:
        mapped = _EVAL_VALUE_MAP.get(value, value)
        return ZeroDenominatorPolicy(mapped)
from datp_core.evaluation.specs import (
    AggregateMetricDefinition,
    ClusterDiagnosticSpec,
    CrossClientAggregationSpec,
    DispersionMetricSpec,
    HeterogeneityDiagnosticSpec,
    InvariantMetricSpec,
    JsDivergenceSpec,
    MetricDefinition,
    MetricDefinitions,
    MetricRequirement,
    PrecisionPolicySpec,
    QuantileMetricSpec,
    RatioMetricSpec,
    ScalarMetricSpec,
    ThresholdEstimationSpec,
)


def _resolve_scalar(cfg: MetricFormulaConfig) -> ScalarMetricSpec:
    return ScalarMetricSpec(
        formula=cfg.formula,
        unit=MetricUnit(cfg.unit) if cfg.unit else None,
        direction=MetricDirection(cfg.direction) if cfg.direction else None,
        zero_denominator=_safe_denom(cfg.zero_denominator) if cfg.zero_denominator else None,
        requires=tuple(cfg.requires) if cfg.requires is not None else None,
        missing_class_behavior=_safe_eval_enum(MissingClassPolicy, cfg.missing_class_behavior),
    )


def _resolve_ratio(cfg: MetricFormulaConfig) -> RatioMetricSpec:
    return RatioMetricSpec(
        formula=cfg.formula,
        unit=MetricUnit(cfg.unit) if cfg.unit else None,
        direction=MetricDirection(cfg.direction) if cfg.direction else None,
        weighting=_safe_eval_enum(WeightingMode, cfg.weighting),
        denominator_stabilizer=cfg.denominator_stabilizer,
        zero_mean_behavior=_safe_denom(cfg.zero_mean_behavior) if cfg.zero_mean_behavior else None,
        near_zero_mean_threshold_formula=cfg.near_zero_mean_threshold_formula,
        near_zero_mean_threshold_factor=cfg.near_zero_mean_threshold_factor,
        near_zero_mean_behavior=_safe_denom(cfg.near_zero_mean_behavior)
        if cfg.near_zero_mean_behavior
        else None,
        minimum_client_count=cfg.minimum_client_count,
        zero_sum_behavior=_safe_denom(cfg.zero_sum_behavior) if cfg.zero_sum_behavior else None,
    )


def _resolve_quantile(cfg: MetricFormulaConfig) -> QuantileMetricSpec:
    return QuantileMetricSpec(
        formula=cfg.formula,
        quantile_estimator=QuantileEstimator(cfg.quantile_estimator) if cfg.quantile_estimator else None,
        unit=MetricUnit(cfg.unit) if cfg.unit else None,
        direction=MetricDirection(cfg.direction) if cfg.direction else None,
    )


def _resolve_dispersion(cfg: MetricFormulaConfig) -> DispersionMetricSpec:
    return DispersionMetricSpec(
        formula=cfg.formula,
        unit=MetricUnit(cfg.unit) if cfg.unit else None,
        direction=MetricDirection(cfg.direction) if cfg.direction else None,
    )


def _resolve_invariant(cfg: MetricFormulaConfig) -> InvariantMetricSpec:
    return InvariantMetricSpec(
        unit=MetricUnit(cfg.unit) if cfg.unit else None,
        direction=MetricDirection(cfg.direction) if cfg.direction else None,
        requires_both_classes=cfg.requires_both_classes,
        role=MetricRole(cfg.role) if cfg.role else None,
        invariance_check=cfg.invariance_check,
    )


def resolve_metric_definitions(cfg: MetricDefinitionsConfig) -> MetricDefinitions:
    cross_client = cfg.cross_client_aggregation

    metric_defs: list[MetricDefinition] = []
    for field_name in ("fpr", "tpr", "balanced_accuracy", "macro_f1", "auroc"):
        metric_cfg = getattr(cfg, field_name, None)
        if metric_cfg is not None:
            metric_defs.append(MetricDefinition(
                identifier=_map_metric_name(field_name),
                formula=getattr(metric_cfg, "formula", None) or "",
                unit=MetricUnit(metric_cfg.unit) if getattr(metric_cfg, "unit", None) else MetricUnit("ratio"),
                direction=MetricDirection(metric_cfg.direction) if getattr(metric_cfg, "direction", None) else MetricDirection("lower_is_better"),
                role=MetricRole("model_quality_control") if field_name == "auroc" else MetricRole("primary"),
                requirements=(
                    MetricRequirement("both_classes"),
                ) if field_name == "auroc" else (),
            ))

    js = cfg.heterogeneity_diagnostics.pairwise_js_divergence
    cc_metrics: list[AggregateMetricDefinition] = [
        AggregateMetricDefinition(
            identifier=MetricId("cv_fpr"),
            source_metric=MetricId("cv_fpr"),
            aggregation=AggregationKind("coefficient_of_variation"),
            unit=MetricUnit("ratio"),
            direction=MetricDirection("lower_is_better"),
            role=MetricRole("primary"),
        ),
    ]

    return MetricDefinitions(
        prediction_rule=_safe_eval_enum(PredictionRule, cfg.prediction_rule),
        per_client_before_aggregation=cfg.per_client_before_aggregation,
        test_rows_only=cfg.test_rows_only,
        metrics=tuple(metric_defs),
        cross_client_aggregation=CrossClientAggregationSpec(
            standard_deviation_ddof=cross_client.standard_deviation_ddof,
            cv_instability_threshold_factor=0.01,
            minimum_client_count=getattr(cross_client, "minimum_client_count", None) or 3,
            weighting=WeightingMode("unweighted"),
            quantile_estimator=QuantileEstimator("linear_interpolated_order_statistic"),
            metrics=tuple(cc_metrics),
        ),
        js_divergence=JsDivergenceSpec(
            histogram_bins=js.histogram_bins,
            logarithm_base=js.logarithm_base,
            range_mode=_safe_eval_enum(HistogramRangeMode, "auto"),
            edge_mode=_safe_eval_enum(HistogramEdgeMode, "shared_across_clients"),
            empty_bin_policy=_safe_eval_enum(EmptyBinPolicy, "ignore"),
            pairwise_aggregation=_safe_eval_enum(PairwiseAggregationMode, js.pairwise_aggregation),
            minimum_client_count=js.minimum_client_count,
        ),
        precision_policy=PrecisionPolicySpec(
            computation=_safe_eval_enum(PrecisionComputation, cfg.precision_policy.computation),
            rounding=_safe_eval_enum(RoundingMode, cfg.precision_policy.rounding),
        ),
        metric_statuses=tuple(MetricStatus(s) for s in cfg.metric_statuses),
        forbidden_substitutions=tuple(cfg.forbidden_substitutions),
    )


def resolve_threshold_exchange_entry(cfg: ThresholdExchangeEntryConfig) -> ThresholdExchangeEntryRecord:
    return ThresholdExchangeEntryRecord(
        uplink_fields_per_client=(
            tuple(cfg.uplink_fields_per_client) if cfg.uplink_fields_per_client is not None else None
        ),
        downlink_fields_per_client=(
            tuple(cfg.downlink_fields_per_client) if cfg.downlink_fields_per_client is not None else None
        ),
        candidate_grid_downlink_fields_per_client=(
            tuple(cfg.candidate_grid_downlink_fields_per_client)
            if cfg.candidate_grid_downlink_fields_per_client is not None
            else None
        ),
        candidate_grid_uplink_fields_per_client_per_candidate=(
            tuple(cfg.candidate_grid_uplink_fields_per_client_per_candidate)
            if cfg.candidate_grid_uplink_fields_per_client_per_candidate is not None
            else None
        ),
    )


def resolve_communication_estimation_contract(
    cfg: CommunicationEstimationContractConfig,
) -> CommunicationEstimationContractRecord:
    exchange = cfg.threshold_exchange
    return CommunicationEstimationContractRecord(
        estimate_basis=cfg.estimate_basis,
        field_encodings={
            key: FieldEncodingRecord(bytes_per_field=v.bytes_per_field, byte_order=v.byte_order)
            for key, v in cfg.field_encodings.items()
        },
        threshold_exchange=ThresholdExchangeRecord(
            direction=exchange.direction,
            b1=resolve_threshold_exchange_entry(exchange.b1),
            b2=resolve_threshold_exchange_entry(exchange.b2),
            b4=resolve_threshold_exchange_entry(exchange.b4),
            federated_summary=resolve_threshold_exchange_entry(exchange.federated_summary),
        ),
        candidate_grid_payload=cfg.candidate_grid_payload,
        model_exchange=ModelExchangeRecord(
            field_width=cfg.model_exchange.field_width,
            directions=tuple(cfg.model_exchange.directions),
            bytes_per_round_formula=cfg.model_exchange.bytes_per_round_formula,
        ),
        checkpoint_storage=CheckpointStorageRecord(
            contents=tuple(cfg.checkpoint_storage.contents),
            model_parameter_bytes_formula=cfg.checkpoint_storage.model_parameter_bytes_formula,
        ),
    )


def resolve_operational_inputs(cfg: OperationalInputsConfig) -> OperationalInputsRecord:
    rate = cfg.benign_decision_rate
    return OperationalInputsRecord(
        benign_decision_rate=BenignDecisionRateRecord(
            configured=rate.configured,
            value=rate.value,
            required_fields=tuple(rate.required_fields),
            finite_value_validation=rate.finite_value_validation,
            non_negative_validation=rate.non_negative_validation,
            unavailable_behavior=rate.unavailable_behavior,
            invented_rate_forbidden=rate.invented_rate_forbidden,
        )
    )
