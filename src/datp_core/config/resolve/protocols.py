"""Protocol-resolution functions extracted from the monolithic resolver.

Ownership boundary: converts authored protocol Pydantic models (protocols.yaml) into immutable
domain records owned by the packages that actually consume them (thresholding, evaluation,
analysis, reporting, artifacts). Exports a narrow function surface; does not import pipeline
execution, CLI, or infrastructure.

``SeedNamespaceRecord``/``ProtocolDeterminismRecord`` (protocols.yaml's own seed/determinism
contract, distinct from runtime.yaml's execution determinism in ``config/resolve/runtime.py``)
have no consumer outside configuration itself, so they are defined directly here rather than in a
separate models file.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import cast

from attrs import define

from datp_core.artifacts.models import ArtifactFingerprintsRecord, ArtifactIdentityRecord
from datp_core.config.loading import ConfigurationError
from datp_core.config.schema.protocols import (
    ArtifactIdentityConfig,
    AuthoredProtocolsConfig,
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
from datp_core.contracts.protocols import (
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
    StatisticalMethod,
    StatisticalProfileRecord,
    ThresholdExchangeEntryRecord,
    ThresholdExchangeRecord,
)
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
from datp_core.core.values import (
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    Probability,
    Seed,
    TypedDomainRegistry,
    deep_freeze,
)
from datp_core.data.contracts import EligibilityFallbackRecord, EligibilityPolicyRecord, NormalizationStrategyRecord
from datp_core.evaluation.models import (
    ClusterDiagnosticsRecord,
    CrossClientAggregationRecord,
    EvaluationResultContractRecord,
    HeterogeneityDiagnosticsRecord,
    JsDivergenceRecord,
    MetricBundleRecord,
    MetricDefinitionsRecord,
    MetricFormulaRecord,
    PrecisionPolicyRecord,
    ThresholdEstimationMetricsRecord,
)
from datp_core.learning.models import (
    BatchingRecord,
    CheckpointAuthorization,
    CheckpointConvergenceRecord,
    CheckpointProfileRecord,
    CheckpointSelectionRecord,
    FederationProfileRecord,
    ModelArchitectureRecord,
    OptimizerRecord,
    PersonalizationStrategy,
    SeedCohortRecord,
    TrainingProfileKind,
    TrainingProfileRecord,
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
    QuantileEstimatorRecord,
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
        near_zero_mean_threshold_factor=cfg.near_zero_mean_threshold_factor,
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
    normalization_strategies: TypedDomainRegistry[NormalizationStrategyId, NormalizationStrategyRecord]
    quantile_estimators: TypedDomainRegistry[str, QuantileEstimatorRecord]
    metric_bundles: TypedDomainRegistry[MetricBundleId, MetricBundleRecord]
    report_profiles: TypedDomainRegistry[str, ReportProfileRecord]
    metric_definitions: MetricDefinitionsRecord
    artifact_identity: ArtifactIdentityRecord
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


def _resolve_training_profiles(authored: AuthoredProtocolsConfig) -> dict[TrainingProfileId, TrainingProfileRecord]:
    training_dict: dict[TrainingProfileId, TrainingProfileRecord] = {}
    for tp_key, tp_cfg in authored.training_profiles.items():
        tp_id = TrainingProfileId(tp_key)
        training_dict[tp_id] = TrainingProfileRecord(
            identifier=tp_id,
            kind=TrainingProfileKind(tp_cfg.kind),
            model_architecture_id=tp_cfg.model_architecture,
            optimizer_id=tp_cfg.optimizer,
            batching_profile_id=tp_cfg.batching,
            local_epochs=(PositiveInt(tp_cfg.local_epochs) if tp_cfg.local_epochs is not None else None),
            participation=tp_cfg.participation,
            checkpoint_authorization=CheckpointAuthorization(tp_cfg.checkpoint_authorization),
            personalization=PersonalizationStrategy(tp_cfg.personalization) if tp_cfg.personalization else None,
            personalized_local_epochs=(
                PositiveInt(tp_cfg.personalized_local_epochs) if tp_cfg.personalized_local_epochs is not None else None
            ),
            personalization_parameter_grid=(
                tuple(tp_cfg.personalization_parameter_grid)
                if tp_cfg.personalization_parameter_grid is not None
                else None
            ),
            proximal_objective=tp_cfg.proximal_objective,
            mu_grid=tuple(tp_cfg.mu_grid) if tp_cfg.mu_grid is not None else None,
            mu_zero_forbidden_as_a_fedprox_condition=tp_cfg.mu_zero_forbidden_as_a_fedprox_condition,
            federation=(
                FederationProfileRecord(
                    fraction_fit=tp_cfg.federation.fraction_fit,
                    fraction_evaluate=tp_cfg.federation.fraction_evaluate,
                    minimum_fit_clients=PositiveInt(tp_cfg.federation.minimum_fit_clients),
                    minimum_evaluate_clients=PositiveInt(tp_cfg.federation.minimum_evaluate_clients),
                    minimum_available_clients=PositiveInt(tp_cfg.federation.minimum_available_clients),
                )
                if tp_cfg.federation is not None
                else None
            ),
        )
    return training_dict


def _resolve_checkpoint_profiles(
    authored: AuthoredProtocolsConfig,
) -> dict[CheckpointProfileId, CheckpointProfileRecord]:
    checkpoint_dict: dict[CheckpointProfileId, CheckpointProfileRecord] = {}
    for cp_key, cp_cfg in authored.checkpoint_profiles.items():
        cp_id = CheckpointProfileId(cp_key)
        selected_rounds = cp_cfg.rounds if cp_cfg.rounds is not None else cp_cfg.epochs
        total_rounds = cp_cfg.total_rounds if cp_cfg.total_rounds is not None else cp_cfg.total_epochs
        if total_rounds is None:
            raise ConfigurationError(f"Checkpoint profile '{cp_key}' has no total rounds or epochs")
        selection_record = CheckpointSelectionRecord(
            rule=cp_cfg.selection.rule,
            tie_break=cp_cfg.selection.tie_break,
            scope=cp_cfg.selection.scope,
            aggregation=cp_cfg.selection.aggregation,
            selected_round_reuse=cp_cfg.selection.selected_round_reuse,
            selection_granularity=cp_cfg.selection.selection_granularity,
            forbidden_selectors=tuple(cp_cfg.selection.forbidden_selectors or ()),
        )
        convergence_record = (
            CheckpointConvergenceRecord(
                metric=cp_cfg.convergence.metric,
                rounds_initial=PositiveInt(cp_cfg.convergence.rounds_initial),
                rule=cp_cfg.convergence.rule,
                formula=cp_cfg.convergence.formula,
                zero_start_loss_behavior=cp_cfg.convergence.zero_start_loss_behavior,
                tolerance=PositiveFloat(cp_cfg.convergence.tolerance),
                window_rounds=PositiveInt(cp_cfg.convergence.window_rounds),
                window=cp_cfg.convergence.window,
                qualification=cp_cfg.convergence.qualification,
                no_qualifying_round_behavior=cp_cfg.convergence.no_qualifying_round_behavior,
            )
            if cp_cfg.convergence is not None
            else None
        )
        checkpoint_dict[cp_id] = CheckpointProfileRecord(
            identifier=cp_id,
            total_rounds=PositiveInt(total_rounds),
            selected_rounds=tuple(PositiveInt(round_number) for round_number in (selected_rounds or ())),
            early_stopping=cp_cfg.early_stopping,
            selection_rule=cp_cfg.selection.rule,
            selection=selection_record,
            convergence=convergence_record,
            checkpoint_save_policy=cp_cfg.checkpoint_save_policy,
        )
    return checkpoint_dict


def _resolve_seed_cohorts(authored: AuthoredProtocolsConfig) -> dict[SeedCohortId, SeedCohortRecord]:
    seed_dict: dict[SeedCohortId, SeedCohortRecord] = {}
    for sc_key, sc_cfg in authored.seed_cohorts.items():
        sc_id = SeedCohortId(sc_key)
        seeds_tuple = tuple(Seed(int(s)) for s in sc_cfg.training_seeds)
        seed_dict[sc_id] = SeedCohortRecord(
            identifier=sc_id,
            paired_seed_count=PositiveInt(len(seeds_tuple)),
            training_seeds=seeds_tuple,
            bootstrap_analysis_seed=Seed(sc_cfg.bootstrap_analysis_seed),
            analysis_seed_model=sc_cfg.analysis_seed_model,
        )
    return seed_dict


def _resolve_statistical_profiles(
    authored: AuthoredProtocolsConfig,
) -> dict[StatisticalProfileId, StatisticalProfileRecord]:
    statistical_dict: dict[StatisticalProfileId, StatisticalProfileRecord] = {}
    for profile_key, profile_cfg in authored.statistical_profiles.items():
        minimum_units = (
            profile_cfg.minimum_paired_units
            if profile_cfg.minimum_paired_units is not None
            else profile_cfg.minimum_units
        )
        profile_id = StatisticalProfileId(profile_key)
        statistical_dict[profile_id] = StatisticalProfileRecord(
            identifier=profile_id,
            method=(StatisticalMethod(profile_cfg.method) if profile_cfg.method is not None else None),
            confidence_level=(
                Probability(profile_cfg.confidence_level) if profile_cfg.confidence_level is not None else None
            ),
            resample_count=(
                PositiveInt(profile_cfg.resample_count) if profile_cfg.resample_count is not None else None
            ),
            minimum_units=PositiveInt(minimum_units) if minimum_units is not None else None,
        )
    return statistical_dict


def _resolve_threshold_policies(authored: AuthoredProtocolsConfig) -> dict[ThresholdPolicyId, ThresholdPolicyRecord]:
    return {
        ThresholdPolicyId(tp_key): _resolve_threshold_policy(tp_cfg)
        for tp_key, tp_cfg in authored.threshold_policies.items()
    }


def _resolve_model_architectures(authored: AuthoredProtocolsConfig) -> dict[str, ModelArchitectureRecord]:
    return {
        key: ModelArchitectureRecord(
            identifier=key,
            kind=m.kind,
            hidden_dims=tuple(PositiveInt(dim) for dim in m.hidden_dims),
            bottleneck_dim=m.bottleneck_dim,
            activation=m.activation,
            activation_placement=m.activation_placement,
            output_activation=m.output_activation,
            normalization_layers=m.normalization_layers,
            bias=m.bias,
            reconstruction_objective=m.reconstruction_objective,
            training_loss_reduction=m.training_loss_reduction,
            precision=m.precision,
            input_dimension_resolution=m.input_dimension.resolution,
            input_dimension_declared_per_dataset=m.input_dimension.declared_per_dataset,
            input_dimension_validation=m.input_dimension.validation,
            decoder_construction=m.decoder.construction,
            decoder_final_layer_output_dim=m.decoder.final_layer_output_dim,
            weight_initialization=m.parameter_initialization.weight,
            bias_initialization=m.parameter_initialization.bias,
            initialization_applied_to=m.parameter_initialization.applied_to,
            initialization_seeded_by=m.parameter_initialization.seeded_by,
            anomaly_score_definition=m.anomaly_score.definition,
            anomaly_score_orientation=m.anomaly_score.orientation,
        )
        for key, m in authored.model_architectures.items()
    }


def _resolve_optimizers(authored: AuthoredProtocolsConfig) -> dict[str, OptimizerRecord]:
    return {
        key: OptimizerRecord(
            identifier=key,
            optimizer_type=o.optimizer_type,
            learning_rate=PositiveFloat(o.learning_rate),
            beta_1=o.beta_1,
            beta_2=o.beta_2,
            epsilon=PositiveFloat(o.epsilon),
            weight_decay=NonNegativeFloat(o.weight_decay),
            amsgrad=o.amsgrad,
            scheduler=o.scheduler,
            gradient_clipping=o.gradient_clipping,
            state_lifecycle=o.state_lifecycle,
            state_aggregated_by_server=o.state_aggregated_by_server,
        )
        for key, o in authored.optimizers.items()
    }


def _resolve_batching_profiles(authored: AuthoredProtocolsConfig) -> dict[str, BatchingRecord]:
    return {
        key: BatchingRecord(
            identifier=key,
            micro_batch_size=PositiveInt(b.micro_batch_size),
            gradient_accumulation_steps=PositiveInt(b.gradient_accumulation_steps),
            effective_batch_size=PositiveInt(b.effective_batch_size),
            shuffle_each_epoch=b.shuffle_each_epoch,
            shuffle_unit=b.shuffle_unit,
            incomplete_final_batch=b.incomplete_final_batch,
            row_ordering_before_shuffle=b.row_ordering_before_shuffle,
            shuffle_seed_namespace=b.shuffle_seed_namespace,
            worker_seed_namespace=b.worker_seed_namespace,
        )
        for key, b in authored.batching.items()
    }


def _resolve_eligibility_policies(
    authored: AuthoredProtocolsConfig,
) -> dict[EligibilityPolicyId, EligibilityPolicyRecord]:
    return {
        EligibilityPolicyId(k): EligibilityPolicyRecord(
            identifier=EligibilityPolicyId(k),
            minimum_benign_calibration_count=PositiveInt(v.minimum_benign_calibration_count),
            determined_before_test_evaluation=v.determined_before_test_evaluation,
            identical_across_policies_in_one_comparison=v.identical_across_policies_in_one_comparison,
            fpr_evaluable_requires_non_empty_benign_test_denominator=(
                v.fpr_evaluable_requires_non_empty_benign_test_denominator
            ),
            attack_evaluable_requires=tuple(v.attack_evaluable_requires),
            ineligible_clients_excluded_from_primary_dispersion=v.ineligible_clients_excluded_from_primary_dispersion,
            ineligible_client_deployment_fallback=EligibilityFallbackRecord(
                threshold_source=v.ineligible_client_deployment_fallback.threshold_source,
                shared_construction=v.ineligible_client_deployment_fallback.shared_construction,
                reported_status=v.ineligible_client_deployment_fallback.reported_status,
                enters_primary_dispersion=v.ineligible_client_deployment_fallback.enters_primary_dispersion,
            ),
            zero_eligible_clients_behavior=v.zero_eligible_clients_behavior,
            affects_standard_eligibility_minimum=v.affects_standard_eligibility_minimum,
            permitted_use=v.permitted_use,
        )
        for k, v in authored.eligibility_policies.items()
    }


def _resolve_normalization_strategies(
    authored: AuthoredProtocolsConfig,
) -> dict[NormalizationStrategyId, NormalizationStrategyRecord]:
    return {
        NormalizationStrategyId(k): NormalizationStrategyRecord(
            identifier=NormalizationStrategyId(k),
            formula=v.formula,
            fitted_statistics=tuple(v.fitted_statistics),
            constant_feature_rule=v.constant_feature_rule,
            out_of_range_transform_values=v.out_of_range_transform_values,
            fit_population=v.fit_population,
            standard_deviation_ddof=v.standard_deviation_ddof,
        )
        for k, v in authored.normalization_strategies.items()
    }


def _resolve_quantile_estimators(authored: AuthoredProtocolsConfig) -> dict[str, QuantileEstimatorRecord]:
    return {
        k: QuantileEstimatorRecord(
            identifier=k,
            sort_order=v.sort_order,
            index_formula=v.index_formula,
            interpolation=v.interpolation,
            single_element_behavior=v.single_element_behavior,
            empty_input_behavior=v.empty_input_behavior,
            non_finite_input_behavior=v.non_finite_input_behavior,
            tie_behavior=v.tie_behavior,
        )
        for k, v in authored.quantile_estimators.items()
    }


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


def resolve_protocols(authored: AuthoredProtocolsConfig) -> ResolvedProtocols:
    """Resolve the authored protocol document (protocols.yaml) into every immutable protocol record."""
    resolved_communication_estimation = (
        cast(dict, deep_freeze(authored.communication_estimation))
        if authored.communication_estimation is not None
        else None
    )
    return ResolvedProtocols(
        training_profiles=TypedDomainRegistry(_items=_resolve_training_profiles(authored)),
        checkpoint_profiles=TypedDomainRegistry(_items=_resolve_checkpoint_profiles(authored)),
        seed_cohorts=TypedDomainRegistry(_items=_resolve_seed_cohorts(authored)),
        statistical_profiles=TypedDomainRegistry(_items=_resolve_statistical_profiles(authored)),
        threshold_policies=_resolve_threshold_policies(authored),
        model_architectures=TypedDomainRegistry(_items=_resolve_model_architectures(authored)),
        optimizers=TypedDomainRegistry(_items=_resolve_optimizers(authored)),
        batching_profiles=TypedDomainRegistry(_items=_resolve_batching_profiles(authored)),
        eligibility_policies=TypedDomainRegistry(_items=_resolve_eligibility_policies(authored)),
        normalization_strategies=TypedDomainRegistry(_items=_resolve_normalization_strategies(authored)),
        quantile_estimators=TypedDomainRegistry(_items=_resolve_quantile_estimators(authored)),
        metric_bundles=TypedDomainRegistry(_items=_resolve_metric_bundles(authored)),
        report_profiles=TypedDomainRegistry(
            _items={key: _resolve_report_profile(key, v) for key, v in authored.report_profiles.items()}
        ),
        metric_definitions=_resolve_metric_definitions(authored.metric_definitions),
        artifact_identity=_resolve_artifact_identity(authored.artifact_identity),
        communication_estimation_contract=_resolve_communication_estimation_contract(
            authored.communication_estimation_contract
        ),
        operational_inputs=_resolve_operational_inputs(authored.operational_inputs),
        communication_estimation=resolved_communication_estimation,
        protocol_determinism=_resolve_protocol_determinism(authored.determinism),
        normalization_fit_scopes=dict(authored.normalization_fit_scopes),
        normalization_leakage_rule=authored.normalization_leakage_rule,
        threshold_policy_defaults=_resolve_threshold_policy_defaults(authored.threshold_policy_defaults),
        nested_replicate_policy=_resolve_nested_replicate_policy(authored.nested_replicate_policy),
        result_types=TypedDomainRegistry(
            _items={key: _resolve_result_type(key, v) for key, v in authored.result_types.items()}
        ),
        evaluation_result_contract=_resolve_evaluation_result_contract(authored.evaluation_result_contract),
        report_defaults=_resolve_report_defaults(authored.report_defaults),
    )
