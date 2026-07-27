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
    MetricDirection,
    MetricRole,
    MetricUnit,
    MissingClassPolicy,
    QuantileEstimator,
    WeightingMode,
    ZeroDenominatorPolicy,
)
from datp_core.evaluation.specs import (
    ClusterDiagnosticSpec,
    CrossClientAggregationSpec,
    DispersionMetricSpec,
    HeterogeneityDiagnosticSpec,
    InvariantMetricSpec,
    JsDivergenceSpec,
    MetricDefinitions,
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
        zero_denominator=ZeroDenominatorPolicy(cfg.zero_denominator) if cfg.zero_denominator else None,
        requires=tuple(cfg.requires) if cfg.requires is not None else None,
        missing_class_behavior=MissingClassPolicy(cfg.missing_class_behavior) if cfg.missing_class_behavior else None,
    )


def _resolve_ratio(cfg: MetricFormulaConfig) -> RatioMetricSpec:
    return RatioMetricSpec(
        formula=cfg.formula,
        unit=MetricUnit(cfg.unit) if cfg.unit else None,
        direction=MetricDirection(cfg.direction) if cfg.direction else None,
        weighting=WeightingMode(cfg.weighting) if cfg.weighting else None,
        denominator_stabilizer=cfg.denominator_stabilizer,
        zero_mean_behavior=ZeroDenominatorPolicy(cfg.zero_mean_behavior) if cfg.zero_mean_behavior else None,
        near_zero_mean_threshold_formula=cfg.near_zero_mean_threshold_formula,
        near_zero_mean_threshold_factor=cfg.near_zero_mean_threshold_factor,
        near_zero_mean_behavior=ZeroDenominatorPolicy(cfg.near_zero_mean_behavior) if cfg.near_zero_mean_behavior else None,
        minimum_client_count=cfg.minimum_client_count,
        zero_sum_behavior=ZeroDenominatorPolicy(cfg.zero_sum_behavior) if cfg.zero_sum_behavior else None,
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
    threshold_est = cfg.threshold_estimation
    js = cfg.heterogeneity_diagnostics.pairwise_js_divergence
    cluster = cfg.cluster_diagnostics
    return MetricDefinitions(
        prediction_rule=cfg.prediction_rule,
        per_client_before_aggregation=cfg.per_client_before_aggregation,
        test_rows_only=cfg.test_rows_only,
        fpr=_resolve_scalar(cfg.fpr),
        tpr=_resolve_scalar(cfg.tpr),
        balanced_accuracy=_resolve_scalar(cfg.balanced_accuracy),
        macro_f1=_resolve_scalar(cfg.macro_f1),
        auroc=_resolve_invariant(cfg.auroc),
        cross_client_aggregation=CrossClientAggregationSpec(
            mean_fpr=_resolve_scalar(cross_client.mean_fpr),
            standard_deviation_ddof=cross_client.standard_deviation_ddof,
            cv_fpr=_resolve_ratio(cross_client.cv_fpr),
            cv_tpr=_resolve_ratio(cross_client.cv_tpr),
            iqr_fpr=_resolve_quantile(cross_client.iqr_fpr),
            fpr_range=_resolve_dispersion(cross_client.fpr_range),
            worst_client_fpr=_resolve_dispersion(cross_client.worst_client_fpr),
            p10_macro_f1=_resolve_quantile(cross_client.p10_macro_f1),
            worst_client_ba=_resolve_dispersion(cross_client.worst_client_ba),
            jain_index=_resolve_ratio(cross_client.jain_index),
            gini_coefficient=_resolve_ratio(cross_client.gini_coefficient),
        ),
        threshold_estimation=ThresholdEstimationSpec(
            absolute_threshold_error=_resolve_scalar(threshold_est.absolute_threshold_error),
            relative_threshold_error=_resolve_ratio(threshold_est.relative_threshold_error),
            oracle_definition=threshold_est.oracle_definition,
            target_exceedance=_resolve_scalar(threshold_est.target_exceedance),
            signed_attainment_error=_resolve_scalar(threshold_est.signed_attainment_error),
            absolute_attainment_error=_resolve_scalar(threshold_est.absolute_attainment_error),
            threshold_dispersion=_resolve_ratio(threshold_est.threshold_dispersion),
            threshold_variance_across_replicates=_resolve_ratio(
                threshold_est.threshold_variance_across_replicates
            ),
        ),
        heterogeneity_diagnostics=HeterogeneityDiagnosticSpec(
            pairwise_js_divergence=JsDivergenceSpec(
                definition=js.definition,
                histogram_bins=js.histogram_bins,
                binning_range=js.binning_range,
                binning_edges=js.binning_edges,
                logarithm_base=js.logarithm_base,
                empty_bin_handling=js.empty_bin_handling,
                pairwise_aggregation=js.pairwise_aggregation,
                unit=js.unit,
                direction=js.direction,
                minimum_client_count=js.minimum_client_count,
            )
        ),
        cluster_diagnostics=ClusterDiagnosticSpec(
            adjusted_rand_index=_resolve_scalar(cluster.adjusted_rand_index),
            within_cluster_dispersion=_resolve_dispersion(cluster.within_cluster_dispersion),
            across_cluster_dispersion=_resolve_dispersion(cluster.across_cluster_dispersion),
        ),
        precision_policy=PrecisionPolicySpec(
            computation=cfg.precision_policy.computation,
            rounding=cfg.precision_policy.rounding,
        ),
        metric_statuses=tuple(cfg.metric_statuses),
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
