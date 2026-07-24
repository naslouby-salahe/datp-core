"""Resolution of operational analysis, communication estimation, and metric definition records."""

from __future__ import annotations

from types import MappingProxyType

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
from datp_core.evaluation import (
    ClusterDiagnosticsRecord,
    CrossClientAggregationRecord,
    HeterogeneityDiagnosticsRecord,
    JsDivergenceRecord,
    MetricDefinitionsRecord,
    MetricFormulaRecord,
    PrecisionPolicyRecord,
    ThresholdEstimationMetricsRecord,
)


def resolve_metric_formula(cfg: MetricFormulaConfig) -> MetricFormulaRecord:
    return MetricFormulaRecord(
        formula=cfg.formula,
        unit=cfg.unit,
        direction=cfg.direction,
        zero_denominator=cfg.zero_denominator,
        requires=tuple(cfg.requires) if cfg.requires is not None else None,
        missing_class_behavior=cfg.missing_class_behavior,
        requires_both_classes=cfg.requires_both_classes,
        role=cfg.role,
        invariance_check=cfg.invariance_check,
        quantile_estimator=cfg.quantile_estimator,
        zero_sum_behavior=cfg.zero_sum_behavior,
        zero_oracle_behavior=cfg.zero_oracle_behavior,
        zero_mean_behavior=cfg.zero_mean_behavior,
        denominator_stabilizer=cfg.denominator_stabilizer,
        near_zero_mean_threshold_formula=cfg.near_zero_mean_threshold_formula,
        near_zero_mean_behavior=cfg.near_zero_mean_behavior,
        near_zero_mean_threshold_factor=cfg.near_zero_mean_threshold_factor,
        minimum_client_count=cfg.minimum_client_count,
        weighting=cfg.weighting,
        comparison_unit=cfg.comparison_unit,
    )


def resolve_metric_definitions(cfg: MetricDefinitionsConfig) -> MetricDefinitionsRecord:
    cross_client = cfg.cross_client_aggregation
    threshold_est = cfg.threshold_estimation
    js = cfg.heterogeneity_diagnostics.pairwise_js_divergence
    cluster = cfg.cluster_diagnostics
    return MetricDefinitionsRecord(
        prediction_rule=cfg.prediction_rule,
        per_client_before_aggregation=cfg.per_client_before_aggregation,
        test_rows_only=cfg.test_rows_only,
        fpr=resolve_metric_formula(cfg.fpr),
        tpr=resolve_metric_formula(cfg.tpr),
        balanced_accuracy=resolve_metric_formula(cfg.balanced_accuracy),
        macro_f1=resolve_metric_formula(cfg.macro_f1),
        auroc=resolve_metric_formula(cfg.auroc),
        cross_client_aggregation=CrossClientAggregationRecord(
            mean_fpr=resolve_metric_formula(cross_client.mean_fpr),
            standard_deviation_ddof=cross_client.standard_deviation_ddof,
            cv_fpr=resolve_metric_formula(cross_client.cv_fpr),
            cv_tpr=resolve_metric_formula(cross_client.cv_tpr),
            iqr_fpr=resolve_metric_formula(cross_client.iqr_fpr),
            fpr_range=resolve_metric_formula(cross_client.fpr_range),
            worst_client_fpr=resolve_metric_formula(cross_client.worst_client_fpr),
            p10_macro_f1=resolve_metric_formula(cross_client.p10_macro_f1),
            worst_client_ba=resolve_metric_formula(cross_client.worst_client_ba),
            jain_index=resolve_metric_formula(cross_client.jain_index),
            gini_coefficient=resolve_metric_formula(cross_client.gini_coefficient),
        ),
        threshold_estimation=ThresholdEstimationMetricsRecord(
            absolute_threshold_error=resolve_metric_formula(threshold_est.absolute_threshold_error),
            relative_threshold_error=resolve_metric_formula(threshold_est.relative_threshold_error),
            oracle_definition=threshold_est.oracle_definition,
            target_exceedance=resolve_metric_formula(threshold_est.target_exceedance),
            signed_attainment_error=resolve_metric_formula(threshold_est.signed_attainment_error),
            absolute_attainment_error=resolve_metric_formula(threshold_est.absolute_attainment_error),
            threshold_dispersion=resolve_metric_formula(threshold_est.threshold_dispersion),
            threshold_variance_across_replicates=resolve_metric_formula(
                threshold_est.threshold_variance_across_replicates
            ),
        ),
        heterogeneity_diagnostics=HeterogeneityDiagnosticsRecord(
            pairwise_js_divergence=JsDivergenceRecord(
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
        cluster_diagnostics=ClusterDiagnosticsRecord(
            adjusted_rand_index=resolve_metric_formula(cluster.adjusted_rand_index),
            within_cluster_dispersion=resolve_metric_formula(cluster.within_cluster_dispersion),
            across_cluster_dispersion=resolve_metric_formula(cluster.across_cluster_dispersion),
        ),
        precision_policy=PrecisionPolicyRecord(
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
        field_encodings=MappingProxyType(
            {
                key: FieldEncodingRecord(bytes_per_field=v.bytes_per_field, byte_order=v.byte_order)
                for key, v in cfg.field_encodings.items()
            }
        ),
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
        filename_match_is_not_lineage_evidence=cfg.filename_match_is_not_lineage_evidence,
        frozen_artifacts_immutable=cfg.frozen_artifacts_immutable,
        ambiguous_latest_reference=cfg.ambiguous_latest_reference,
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
