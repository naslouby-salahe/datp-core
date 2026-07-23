"""Protocol-resolution functions extracted from the monolithic resolver.

Ownership boundary: converts authored protocol Pydantic models (protocols.yaml) into immutable
domain records owned by the packages that actually consume them (thresholding, evaluation,
analysis, reporting, artifacts). Exports a narrow function surface; does not import pipeline
execution, CLI, or infrastructure.

``SeedNamespaceRecord``/``ProtocolDeterminismRecord`` (protocols.yaml's own seed/determinism
contract, distinct from runtime.yaml's execution determinism in ``configuration/runtime_resolution.py``)
have no consumer outside configuration itself, so they are defined directly here rather than in a
separate models file.
"""

from __future__ import annotations

from types import MappingProxyType

from attrs import define

from datp_core.artifacts.models import ArtifactFingerprintsRecord, ArtifactIdentityRecord
from datp_core.configuration.loading import ConfigurationError
from datp_core.configuration.models import (
    ArtifactIdentityConfig,
    CalibrationFallbackPolicyConfig,
    CentralizedPooledThresholdPolicyConfig,
    ClusterThresholdPolicyConfig,
    CommunicationEstimationContractConfig,
    DeterminismProfileConfig,
    EvaluationResultContractConfig,
    FamilyMeanThresholdPolicyConfig,
    FederatedFixedCoefficientPolicyConfig,
    FederatedMatchedExceedancePolicyConfig,
    LocalGlobalShrinkagePolicyConfig,
    LocalQuantileThresholdPolicyConfig,
    MetricDefinitionsConfig,
    MetricFormulaConfig,
    NestedReplicatePolicyConfig,
    OperationalInputsConfig,
    ReportDefaultsConfig,
    ReportProfileConfig,
    ResultTypeConfig,
    SharedMeanThresholdPolicyConfig,
    SharedPooledThresholdPolicyConfig,
    SharedWeightedThresholdPolicyConfig,
    SplitConformalThresholdPolicyConfig,
    ThresholdExchangeEntryConfig,
    ThresholdPolicyDefaultsConfig,
    TypedThresholdPolicyConfig,
)
from datp_core.evaluation.models import (
    ClusterDiagnosticsRecord,
    CrossClientAggregationRecord,
    EvaluationResultContractRecord,
    HeterogeneityDiagnosticsRecord,
    JsDivergenceRecord,
    MetricDefinitionsRecord,
    MetricFormulaRecord,
    PrecisionPolicyRecord,
    ThresholdEstimationMetricsRecord,
)
from datp_core.pipeline.protocol_types import (
    BenignDecisionRateRecord,
    CheckpointStorageRecord,
    CommunicationEstimationContractRecord,
    FieldEncodingRecord,
    ModelExchangeRecord,
    NestedReplicatePolicyRecord,
    OperationalInputsRecord,
    ReportColumnRecord,
    ReportDefaultsRecord,
    ReportProfileRecord,
    ResultTypeRecord,
    ThresholdExchangeEntryRecord,
    ThresholdExchangeRecord,
)
from datp_core.thresholding.models import (
    CalibrationFallbackThresholdPolicyRecord,
    CentralizedPooledThresholdPolicyRecord,
    ClusterThresholdPolicyRecord,
    FamilyMeanThresholdPolicyRecord,
    FederatedFixedCoefficientThresholdPolicyRecord,
    FederatedMatchedExceedanceThresholdPolicyRecord,
    LocalGlobalShrinkageThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
    SplitConformalThresholdPolicyRecord,
    ThresholdPolicyDefaultsRecord,
    ThresholdPolicyRecord,
)


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
    derived_seed_algorithm: MappingProxyType
    seed_namespaces: MappingProxyType
    resolved_seeds_required_in_manifests: tuple[str, ...]


_THRESHOLD_POLICY_RECORD_TYPES: dict[type[TypedThresholdPolicyConfig], type[ThresholdPolicyRecord]] = {
    SharedMeanThresholdPolicyConfig: SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyConfig: SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyConfig: SharedWeightedThresholdPolicyRecord,
    LocalQuantileThresholdPolicyConfig: LocalQuantileThresholdPolicyRecord,
    FamilyMeanThresholdPolicyConfig: FamilyMeanThresholdPolicyRecord,
    CentralizedPooledThresholdPolicyConfig: CentralizedPooledThresholdPolicyRecord,
    ClusterThresholdPolicyConfig: ClusterThresholdPolicyRecord,
    SplitConformalThresholdPolicyConfig: SplitConformalThresholdPolicyRecord,
    LocalGlobalShrinkagePolicyConfig: LocalGlobalShrinkageThresholdPolicyRecord,
    CalibrationFallbackPolicyConfig: CalibrationFallbackThresholdPolicyRecord,
    FederatedMatchedExceedancePolicyConfig: FederatedMatchedExceedanceThresholdPolicyRecord,
    FederatedFixedCoefficientPolicyConfig: FederatedFixedCoefficientThresholdPolicyRecord,
}


def _resolve_threshold_policy(cfg: TypedThresholdPolicyConfig) -> ThresholdPolicyRecord:
    """Convert an authored threshold-policy variant into its pure domain record, losslessly."""
    record_type = _THRESHOLD_POLICY_RECORD_TYPES.get(type(cfg))
    if record_type is None:
        raise ConfigurationError(f"Unsupported authored threshold policy configuration: {type(cfg).__name__}")
    return record_type(**cfg.model_dump())


def _resolve_metric_formula(cfg: MetricFormulaConfig) -> MetricFormulaRecord:
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
        minimum_client_count=cfg.minimum_client_count,
        weighting=cfg.weighting,
        comparison_unit=cfg.comparison_unit,
    )


def _resolve_metric_definitions(cfg: MetricDefinitionsConfig) -> MetricDefinitionsRecord:
    cross_client = cfg.cross_client_aggregation
    threshold_est = cfg.threshold_estimation
    js = cfg.heterogeneity_diagnostics.pairwise_js_divergence
    cluster = cfg.cluster_diagnostics
    return MetricDefinitionsRecord(
        prediction_rule=cfg.prediction_rule,
        per_client_before_aggregation=cfg.per_client_before_aggregation,
        test_rows_only=cfg.test_rows_only,
        fpr=_resolve_metric_formula(cfg.fpr),
        tpr=_resolve_metric_formula(cfg.tpr),
        balanced_accuracy=_resolve_metric_formula(cfg.balanced_accuracy),
        macro_f1=_resolve_metric_formula(cfg.macro_f1),
        auroc=_resolve_metric_formula(cfg.auroc),
        cross_client_aggregation=CrossClientAggregationRecord(
            mean_fpr=_resolve_metric_formula(cross_client.mean_fpr),
            standard_deviation_ddof=cross_client.standard_deviation_ddof,
            cv_fpr=_resolve_metric_formula(cross_client.cv_fpr),
            cv_tpr=_resolve_metric_formula(cross_client.cv_tpr),
            iqr_fpr=_resolve_metric_formula(cross_client.iqr_fpr),
            fpr_range=_resolve_metric_formula(cross_client.fpr_range),
            worst_client_fpr=_resolve_metric_formula(cross_client.worst_client_fpr),
            p10_macro_f1=_resolve_metric_formula(cross_client.p10_macro_f1),
            worst_client_ba=_resolve_metric_formula(cross_client.worst_client_ba),
            jain_index=_resolve_metric_formula(cross_client.jain_index),
            gini_coefficient=_resolve_metric_formula(cross_client.gini_coefficient),
        ),
        threshold_estimation=ThresholdEstimationMetricsRecord(
            absolute_threshold_error=_resolve_metric_formula(threshold_est.absolute_threshold_error),
            relative_threshold_error=_resolve_metric_formula(threshold_est.relative_threshold_error),
            oracle_definition=threshold_est.oracle_definition,
            target_exceedance=_resolve_metric_formula(threshold_est.target_exceedance),
            signed_attainment_error=_resolve_metric_formula(threshold_est.signed_attainment_error),
            absolute_attainment_error=_resolve_metric_formula(threshold_est.absolute_attainment_error),
            threshold_dispersion=_resolve_metric_formula(threshold_est.threshold_dispersion),
            threshold_variance_across_replicates=_resolve_metric_formula(
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
            adjusted_rand_index=_resolve_metric_formula(cluster.adjusted_rand_index),
            within_cluster_dispersion=_resolve_metric_formula(cluster.within_cluster_dispersion),
            across_cluster_dispersion=_resolve_metric_formula(cluster.across_cluster_dispersion),
        ),
        precision_policy=PrecisionPolicyRecord(
            computation=cfg.precision_policy.computation,
            rounding=cfg.precision_policy.rounding,
        ),
        metric_statuses=tuple(cfg.metric_statuses),
        forbidden_substitutions=tuple(cfg.forbidden_substitutions),
    )


def _resolve_artifact_identity(cfg: ArtifactIdentityConfig) -> ArtifactIdentityRecord:
    fp = cfg.fingerprints
    return ArtifactIdentityRecord(
        hash_function=cfg.hash_function,
        digest_bytes=cfg.digest_bytes,
        canonical_serialization=cfg.canonical_serialization,
        absolute_paths_excluded_from_identity=cfg.absolute_paths_excluded_from_identity,
        fingerprints=ArtifactFingerprintsRecord(
            source=tuple(fp.source),
            schema_stage=tuple(fp.schema_stage),
            materialization=tuple(fp.materialization),
            client_assignment=tuple(fp.client_assignment),
            model_stage=tuple(fp.model_stage),
            training=tuple(fp.training),
            checkpoint=tuple(fp.checkpoint),
            score=tuple(fp.score),
            threshold=tuple(fp.threshold),
            metric=tuple(fp.metric),
            analysis=tuple(fp.analysis),
        ),
        lineage_validation_before_reuse=tuple(cfg.lineage_validation_before_reuse),
        reuse_rejected_when_any_changes=tuple(cfg.reuse_rejected_when_any_changes),
    )


def _resolve_threshold_exchange_entry(cfg: ThresholdExchangeEntryConfig) -> ThresholdExchangeEntryRecord:
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


def _resolve_communication_estimation_contract(
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
            b1=_resolve_threshold_exchange_entry(exchange.b1),
            b2=_resolve_threshold_exchange_entry(exchange.b2),
            b4=_resolve_threshold_exchange_entry(exchange.b4),
            federated_summary=_resolve_threshold_exchange_entry(exchange.federated_summary),
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


def _resolve_operational_inputs(cfg: OperationalInputsConfig) -> OperationalInputsRecord:
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


def _resolve_protocol_determinism(cfg: DeterminismProfileConfig) -> ProtocolDeterminismRecord:
    return ProtocolDeterminismRecord(
        seed_domains=tuple(cfg.seed_domains),
        partition_seed_independent_of_training_seeds=cfg.partition_seed_independent_of_training_seeds,
        checkpoint_selection_uses_no_stochastic_seed=cfg.checkpoint_selection_uses_no_stochastic_seed,
        derived_seed_algorithm=MappingProxyType(dict(cfg.derived_seed_algorithm)),
        seed_namespaces=MappingProxyType(
            {
                key: SeedNamespaceRecord(key=v.key, components=tuple(v.components))
                for key, v in cfg.seed_namespaces.items()
            }
        ),
        resolved_seeds_required_in_manifests=tuple(cfg.resolved_seeds_required_in_manifests),
    )


def _resolve_threshold_policy_defaults(cfg: ThresholdPolicyDefaultsConfig) -> ThresholdPolicyDefaultsRecord:
    return ThresholdPolicyDefaultsRecord(
        source_score_population=cfg.source_score_population,
        eligibility_filter=cfg.eligibility_filter,
        attack_rows_forbidden_in_calibration=cfg.attack_rows_forbidden_in_calibration,
        non_finite_calibration_score=cfg.non_finite_calibration_score,
        empty_client_calibration=cfg.empty_client_calibration,
        application_scope=cfg.application_scope,
        required_diagnostic_fields=tuple(cfg.required_diagnostic_fields),
    )


def _resolve_nested_replicate_policy(cfg: NestedReplicatePolicyConfig) -> NestedReplicatePolicyRecord:
    return NestedReplicatePolicyRecord(
        replicate_values_computed_first=cfg.replicate_values_computed_first,
        summarized_within_seed_before_across_seed_inference=cfg.summarized_within_seed_before_across_seed_inference,
        seed_level_statistic=cfg.seed_level_statistic,
        replicates_counted_as_independent_units=cfg.replicates_counted_as_independent_units,
        additional_required_replicate_statistic=cfg.additional_required_replicate_statistic,
    )


def _resolve_result_type(identifier: str, cfg: ResultTypeConfig) -> ResultTypeRecord:
    return ResultTypeRecord(identifier=identifier, permitted_evidence_roles=tuple(cfg.permitted_evidence_roles))


def _resolve_evaluation_result_contract(cfg: EvaluationResultContractConfig) -> EvaluationResultContractRecord:
    return EvaluationResultContractRecord(
        per_evaluation_result_type=cfg.per_evaluation_result_type,
        per_evaluation_eligibility_result_type=cfg.per_evaluation_eligibility_result_type,
        per_evaluation_required_records=tuple(cfg.per_evaluation_required_records),
    )


def _resolve_report_defaults(cfg: ReportDefaultsConfig) -> ReportDefaultsRecord:
    return ReportDefaultsRecord(
        ordering=cfg.ordering,
        missing_value_policy=cfg.missing_value_policy,
        table_output_formats=tuple(cfg.table_output_formats),
        figure_output_formats=tuple(cfg.figure_output_formats),
        provenance_required_per_artifact=cfg.provenance_required_per_artifact,
        analysis_defined_direction_token=cfg.analysis_defined_direction_token,
    )


def _resolve_report_profile(identifier: str, cfg: ReportProfileConfig) -> ReportProfileRecord:
    return ReportProfileRecord(
        identifier=identifier,
        artifact_type=cfg.artifact_type,
        table_type=cfg.table_type,
        figure_type=cfg.figure_type,
        estimate_basis=cfg.estimate_basis,
        columns=(
            [ReportColumnRecord(name=c.name, unit=c.unit, direction=c.direction) for c in cfg.columns]
            if cfg.columns is not None
            else None
        ),
        series=(
            [ReportColumnRecord(name=c.name, unit=c.unit, direction=c.direction) for c in cfg.series]
            if cfg.series is not None
            else None
        ),
    )
