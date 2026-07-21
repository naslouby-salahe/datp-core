"""Staged resolution pipeline converting authored YAML documents into an immutable ResolvedProjectConfiguration."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import cast

import cattrs
from attrs import define

from datp_core.config.models.dataset_config import CategoricalEncodingConfig
from datp_core.config.models.experiment_config import SweepVariableConfig
from datp_core.config.models.protocol_config import (
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
from datp_core.config.runtime_settings import (
    ResolvedProjectPaths,
    ResolvedRuntimeConfiguration,
    RuntimeBootstrapSettings,
    resolve_config_root,
    resolve_runtime_configuration,
)
from datp_core.config.yaml_loader import ConfigurationError, YamlConfigurationReader
from datp_core.domain.catalogue import (
    AnalysisSpecRecord,
    BatchingRecord,
    CapabilityRequirementRecord,
    CheckpointConvergenceRecord,
    CheckpointProfileRecord,
    CheckpointSelectionRecord,
    ConditionSweepRecord,
    EligibilityFallbackRecord,
    EligibilityPolicyRecord,
    EvaluationSpecRecord,
    EvidenceRole,
    ExperimentRecord,
    FederationProfileRecord,
    MetricBundleRecord,
    ModelArchitectureRecord,
    NormalizationStrategyRecord,
    OptimizerRecord,
    PopulationRecord,
    QuantileEstimatorRecord,
    RunRequirement,
    SeedCohortRecord,
    StatisticalProfileRecord,
    SweepConditionRecord,
    SweepRecord,
    SweepValue,
    TrainingProfileRecord,
    ValueSweepRecord,
)
from datp_core.domain.datasets import (
    AdapterKind,
    ConfiguredSourceTree,
    DatasetInspectionContract,
    DatasetMaterialization,
    DatasetSetup,
    ResolvedDataset,
    ResolvedDatasetPaths,
    SourceLayout,
)
from datp_core.domain.fingerprints import (
    CanonicalProjection,
    Fingerprint,
    canonicalize_value,
    compute_execution_fingerprint,
    compute_scientific_fingerprint,
)
from datp_core.domain.identifiers import (
    CheckpointProfileId,
    DatasetId,
    DatasetSetupId,
    EligibilityPolicyId,
    ExperimentId,
    MaterializationId,
    MetricBundleId,
    NormalizationStrategyId,
    PopulationId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.domain.protocol_contracts import (
    ArtifactFingerprintsRecord,
    ArtifactIdentityRecord,
    BenignDecisionRateRecord,
    CheckpointStorageRecord,
    ClusterDiagnosticsRecord,
    CommunicationEstimationContractRecord,
    CrossClientAggregationRecord,
    EvaluationResultContractRecord,
    FieldEncodingRecord,
    HeterogeneityDiagnosticsRecord,
    JsDivergenceRecord,
    MetricDefinitionsRecord,
    MetricFormulaRecord,
    ModelExchangeRecord,
    NestedReplicatePolicyRecord,
    OperationalInputsRecord,
    PrecisionPolicyRecord,
    ProtocolDeterminismRecord,
    ReportColumnRecord,
    ReportDefaultsRecord,
    ReportProfileRecord,
    ResultTypeRecord,
    SeedNamespaceRecord,
    ThresholdEstimationMetricsRecord,
    ThresholdExchangeEntryRecord,
    ThresholdExchangeRecord,
    ThresholdPolicyDefaultsRecord,
)
from datp_core.domain.thresholding import (
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
    ThresholdPolicyRecord,
)
from datp_core.domain.values import (
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    Probability,
    RelativePath,
    Seed,
    TypedDomainRegistry,
    deep_freeze,
)

_projection_converter = cattrs.Converter()


def _unstructure(value: object) -> object:
    """Convert resolved attrs records into primitive structures for canonical fingerprinting."""
    return _projection_converter.unstructure(value)


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


def _resolve_sweep_value(value: object) -> SweepValue:
    if isinstance(value, list):
        if not all(isinstance(item, str) for item in value):
            raise ConfigurationError(f"Sweep value list must contain only strings, got: {value!r}")
        return tuple(value)
    if isinstance(value, str | int | float):
        return value
    raise ConfigurationError(f"Unsupported authored sweep value: {value!r}")


def _resolve_sweep(name: str, cfg: SweepVariableConfig) -> SweepRecord:
    if cfg.values is not None:
        return ValueSweepRecord(name=name, values=tuple(_resolve_sweep_value(value) for value in cfg.values))
    assert cfg.conditions is not None  # enforced by SweepVariableConfig.validate_exactly_one_variant
    return ConditionSweepRecord(
        name=name,
        conditions=tuple(
            SweepConditionRecord(name=c.name, allocation=c.allocation, dirichlet_alpha=c.dirichlet_alpha)
            for c in cfg.conditions
        ),
    )


@define(frozen=True, slots=True, kw_only=True)
class ResolvedProjectConfiguration:
    """Single resolved project configuration authority loaded once during composition root initialization."""

    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfileRecord]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortRecord]
    statistical_profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]
    threshold_policies: TypedDomainRegistry[ThresholdPolicyId, ThresholdPolicyRecord]
    model_architectures: TypedDomainRegistry[str, ModelArchitectureRecord]
    optimizers: TypedDomainRegistry[str, OptimizerRecord]
    batching_profiles: TypedDomainRegistry[str, BatchingRecord]
    eligibility_policies: TypedDomainRegistry[EligibilityPolicyId, EligibilityPolicyRecord]
    normalization_strategies: TypedDomainRegistry[NormalizationStrategyId, NormalizationStrategyRecord]
    quantile_estimators: TypedDomainRegistry[str, QuantileEstimatorRecord]
    metric_bundles: TypedDomainRegistry[MetricBundleId, MetricBundleRecord]
    metric_definitions: MetricDefinitionsRecord
    artifact_identity: ArtifactIdentityRecord
    communication_estimation_contract: CommunicationEstimationContractRecord
    operational_inputs: OperationalInputsRecord
    report_profiles: TypedDomainRegistry[str, ReportProfileRecord]
    communication_estimation: Mapping[str, object] | None
    protocol_determinism: ProtocolDeterminismRecord
    normalization_fit_scopes: Mapping[str, str]
    normalization_leakage_rule: str
    threshold_policy_defaults: ThresholdPolicyDefaultsRecord
    nested_replicate_policy: NestedReplicatePolicyRecord
    result_types: TypedDomainRegistry[str, ResultTypeRecord]
    evaluation_result_contract: EvaluationResultContractRecord
    report_defaults: ReportDefaultsRecord
    runtime: ResolvedRuntimeConfiguration
    paths: ResolvedProjectPaths
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    scientific_projection: CanonicalProjection
    execution_projection: CanonicalProjection


def _resolve_adapter_kind(dataset_name: str) -> AdapterKind:
    try:
        return AdapterKind(dataset_name.lower())
    except ValueError as exc:
        raise ConfigurationError(f"Unsupported dataset adapter kind: {dataset_name}") from exc


def resolve_project_configuration(
    config_dir: Path | None = None,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ResolvedProjectConfiguration:
    """Execute staged configuration resolution pipeline."""
    # execution_profile is required from the environment (DATP_EXECUTION_PROFILE), not a default;
    # see the matching comment in config/runtime_settings.py.
    bootstrap_settings = bootstrap_settings or RuntimeBootstrapSettings()  # pyright: ignore[reportCallIssue]
    if config_dir is None:
        config_dir = resolve_config_root(bootstrap_settings)
    config_dir = config_dir.resolve()
    datasets_dir = config_dir / "datasets"

    dataset_paths = tuple(sorted(datasets_dir.glob("*.yaml")))
    if not dataset_paths:
        raise ConfigurationError("No dataset configuration documents found", source_path=datasets_dir)
    experiments_path = config_dir / "experiments.yaml"
    protocols_path = config_dir / "protocols.yaml"
    runtime_path = config_dir / "runtime.yaml"

    authored_datasets, authored_experiments, authored_protocols, authored_runtime = (
        YamlConfigurationReader.read_project_documents(
            dataset_paths=dataset_paths,
            experiments_path=experiments_path,
            protocols_path=protocols_path,
            runtime_path=runtime_path,
        )
    )

    resolved_runtime = resolve_runtime_configuration(
        authored_runtime=authored_runtime,
        bootstrap_settings=bootstrap_settings,
    )
    paths = resolved_runtime.paths

    # 1. Resolve datasets
    resolved_datasets: dict[DatasetId, ResolvedDataset] = {}
    for d_cfg in authored_datasets:
        d_id = DatasetId(d_cfg.dataset)
        if d_id in resolved_datasets:
            raise ConfigurationError(f"Duplicate dataset identifier across dataset documents: '{d_cfg.dataset}'")
        adapter_kind = _resolve_adapter_kind(d_cfg.dataset)
        raw_root = d_cfg.source_layout.root
        dataset_paths = ResolvedDatasetPaths(
            raw_data_root=paths.raw_data,
            raw_root=(paths.raw_data / raw_root).resolve(),
            processed_root=(paths.processed_data / d_cfg.dataset).resolve(),
        )
        setups = tuple(
            DatasetSetup(
                identifier=DatasetSetupId(identifier),
                materialization_id=MaterializationId(setup.materialization),
                capabilities=tuple(setup.provides_capabilities),
            )
            for identifier, setup in sorted(d_cfg.setups.items())
        )
        materializations = tuple(
            DatasetMaterialization(
                identifier=MaterializationId(identifier),
                role=materialization.role,
                normalization_strategy=materialization.normalization.strategy,
                normalization_scope=materialization.normalization.scope,
                vocabulary_fit_split=materialization.vocabulary_fit_split,
                preprocessing_sequence=tuple(materialization.preprocessing_sequence),
                row_exclusion=materialization.row_exclusion,
                split_row_semantics=(
                    cast(Mapping[str, "str | bool"], deep_freeze(materialization.split_row_semantics))
                    if materialization.split_row_semantics is not None
                    else None
                ),
                infeasibility_policy=materialization.infeasibility_policy,
                split_method=materialization.split.method,
                split_seed=Seed(materialization.split.split_seed)
                if materialization.split.split_seed is not None
                else None,
                split_ratios=tuple(
                    (role, Probability(ratio)) for role, ratio in sorted((materialization.split.ratios or {}).items())
                ),
                chronological_ratios=tuple(
                    (role, Probability(value))
                    for role, value in (
                        ("historical_train", materialization.split.historical_train_fraction),
                        ("historical_calibration", materialization.split.historical_calibration_fraction),
                        ("future_recalibration", materialization.split.future_recalibration_fraction),
                        ("future_evaluation", materialization.split.future_evaluation_fraction),
                    )
                    if value is not None
                ),
                split_ordering_basis=materialization.split.ordering_basis,
                split_ordering_scope=materialization.split.ordering_scope,
                split_gap_handling=materialization.split.gap_handling,
                split_attack_rows=materialization.split.attack_rows,
                split_attack_test_membership=materialization.split.attack_test_membership,
                split_attack_ordering=materialization.split.attack_ordering,
                split_benign_attack_deduplication=materialization.split.benign_attack_deduplication,
                split_role_order=(
                    tuple(materialization.split.role_order) if materialization.split.role_order is not None else None
                ),
                split_excluded_client_folders=(
                    tuple(materialization.split.excluded_client_folders)
                    if materialization.split.excluded_client_folders is not None
                    else None
                ),
                split_exclusion_reason=materialization.split.exclusion_reason,
                split_ordering_field=materialization.split.ordering_field,
                split_ordering_sort=materialization.split.ordering_sort,
                split_rollover_policy=materialization.split.rollover_policy,
                split_rollover_scope=materialization.split.rollover_scope,
                split_boundary_rule=materialization.split.boundary_rule,
                split_boundary_index_formula=materialization.split.boundary_index_formula,
                split_future_leakage_check=materialization.split.future_leakage_check,
                split_minimum_row_counts=(
                    cast(Mapping[str, int], deep_freeze(materialization.split.minimum_row_counts))
                    if materialization.split.minimum_row_counts is not None
                    else None
                ),
                split_missing_client_policy=materialization.split.missing_client_policy,
                split_chronology_unverifiable_policy=materialization.split.chronology_unverifiable_policy,
            )
            for identifier, materialization in sorted(d_cfg.materializations.items())
        )
        source_column_count = d_cfg.field_schema.source_column_count
        configured_sources = d_cfg.source_layout.sources
        if d_cfg.field_schema.model_features is not None:
            required_model_headers = tuple(d_cfg.field_schema.model_features.order)
        elif d_cfg.field_schema.retained_numeric_features is not None:
            required_model_headers = tuple(d_cfg.field_schema.retained_numeric_features.order)
        else:
            raise ConfigurationError(f"Dataset '{d_cfg.dataset}' has no resolved model feature headers")
        categorical_encoding = d_cfg.field_schema.categorical_encoding
        required_categorical_headers = (
            tuple(categorical_encoding.columns) if isinstance(categorical_encoding, CategoricalEncodingConfig) else ()
        )
        multiclass_label = d_cfg.field_schema.label_fields.multiclass_label
        label_header = multiclass_label.column if multiclass_label is not None else None
        if configured_sources is None:
            if d_cfg.source_layout.attack_file_pattern is None:
                raise ConfigurationError(
                    f"Dataset '{d_cfg.dataset}' has a single unconfigured source tree "
                    "and must author an explicit 'attack_file_pattern'"
                )
            source_trees = (
                ConfiguredSourceTree(
                    identifier="primary",
                    root=RelativePath(d_cfg.source_layout.root),
                    file_pattern=d_cfg.source_layout.attack_file_pattern,
                    expected_column_count=(
                        source_column_count
                        if isinstance(source_column_count, int)
                        else next(iter(source_column_count.values()))
                    ),
                    executable=True,
                    required_headers=required_model_headers + required_categorical_headers,
                ),
            )
        else:
            source_trees = tuple(
                ConfiguredSourceTree(
                    identifier=identifier,
                    root=RelativePath(source.root),
                    file_pattern=source.file_pattern,
                    expected_column_count=(
                        source_column_count if isinstance(source_column_count, int) else source_column_count[identifier]
                    ),
                    executable=source.role == "executable",
                    required_headers=(
                        required_model_headers
                        + required_categorical_headers
                        + ((label_header,) if source.role == "executable" and label_header is not None else ())
                    ),
                )
                for identifier, source in sorted(configured_sources.items())
            )
        inspection_contract = DatasetInspectionContract(
            source_trees=source_trees,
            require_identical_headers=(
                d_cfg.field_schema.header_must_be_identical_across_all_source_files is True
                or d_cfg.field_schema.header_must_be_identical_across_all_files_in_a_tree is True
            ),
            device_directories=tuple(d_cfg.source_layout.device_dirs or ()),
            benign_filename=d_cfg.source_layout.benign_file,
            benign_file_required_per_device=d_cfg.source_layout.benign_file_required_per_device is True,
            attack_family_directories=tuple(d_cfg.source_layout.attack_family_dirs or ()),
            attack_family_required_per_device=d_cfg.source_layout.attack_family_required_per_device is True,
            normal_group_directories=tuple(d_cfg.source_layout.normal_group_folders or ()),
            attack_filenames=tuple(d_cfg.source_layout.attack_files or ()),
            ignored_root_entries=tuple(d_cfg.source_layout.ignored_root_entries),
            benign_label=(
                str(d_cfg.field_schema.label_fields.binary_label.get("benign_value"))
                if d_cfg.field_schema.label_fields.binary_label is not None
                and isinstance(d_cfg.field_schema.label_fields.binary_label.get("benign_value"), str)
                else None
            ),
            normal_traffic_root=(
                RelativePath(d_cfg.source_layout.normal_traffic_root)
                if d_cfg.source_layout.normal_traffic_root is not None
                else None
            ),
            attack_traffic_root=(
                RelativePath(d_cfg.source_layout.attack_traffic_root)
                if d_cfg.source_layout.attack_traffic_root is not None
                else None
            ),
            binary_label_header=(
                str(d_cfg.field_schema.label_fields.binary_label.get("column"))
                if isinstance(d_cfg.field_schema.label_fields.binary_label.get("column"), str)
                else None
            ),
        )
        resolved_datasets[d_id] = ResolvedDataset(
            dataset_id=d_id,
            adapter_kind=adapter_kind,
            display_name=d_cfg.display_name,
            schema_id=d_cfg.schema_id,
            source_layout=SourceLayout(
                root=RelativePath(d_cfg.source_layout.root),
                ignored_suffixes=tuple(d_cfg.source_layout.ignored_source_suffixes),
                ignored_subtrees=tuple(d_cfg.source_layout.ignored_subtrees),
            ),
            inspection_contract=inspection_contract,
            setups=setups,
            materializations=materializations,
            eligibility_policy_id=EligibilityPolicyId(d_cfg.eligibility_policy),
            capabilities=tuple(sorted({capability for setup in setups for capability in setup.capabilities})),
            paths=dataset_paths,
            fingerprint_source_fields=tuple(d_cfg.fingerprint_inputs.source),
            fingerprint_schema_fields=tuple(d_cfg.fingerprint_inputs.schema_fields),
            fingerprint_materialization_fields=tuple(d_cfg.fingerprint_inputs.materialization),
            fingerprint_client_assignment_fields=tuple(d_cfg.fingerprint_inputs.client_assignment),
        )

    # 2. Resolve study populations & validate cross-references
    populations_dict: dict[PopulationId, PopulationRecord] = {}
    for pop_key, pop_cfg in authored_experiments.study_populations.items():
        pop_id = PopulationId(pop_key)
        target_dataset_id = DatasetId(pop_cfg.dataset)
        if target_dataset_id not in resolved_datasets:
            raise ConfigurationError(f"Population '{pop_key}' references unregistered dataset '{pop_cfg.dataset}'")
        dataset_obj = resolved_datasets[target_dataset_id]
        setup_id = DatasetSetupId(pop_cfg.setup)
        if not any(setup.identifier == setup_id for setup in dataset_obj.setups):
            raise ConfigurationError(
                f"Population '{pop_key}' references unregistered setup '{pop_cfg.setup}' in dataset '{pop_cfg.dataset}'"
            )

        metric_bundle_id = MetricBundleId(pop_cfg.metric_bundle)
        if pop_cfg.metric_bundle not in authored_protocols.metric_bundles:
            raise ConfigurationError(
                f"Population '{pop_key}' references unregistered metric bundle '{pop_cfg.metric_bundle}'"
            )

        populations_dict[pop_id] = PopulationRecord(
            identifier=pop_id,
            dataset_id=target_dataset_id,
            setup_id=setup_id,
            metric_bundle_id=metric_bundle_id,
        )
    populations_reg = TypedDomainRegistry(_items=populations_dict)

    # 3. Resolve training profiles
    training_dict: dict[TrainingProfileId, TrainingProfileRecord] = {}
    for tp_key, tp_cfg in authored_protocols.training_profiles.items():
        tp_id = TrainingProfileId(tp_key)
        training_dict[tp_id] = TrainingProfileRecord(
            identifier=tp_id,
            kind=tp_cfg.kind,
            model_architecture_id=tp_cfg.model_architecture,
            optimizer_id=tp_cfg.optimizer,
            batching_profile_id=tp_cfg.batching,
            local_epochs=(PositiveInt(tp_cfg.local_epochs) if tp_cfg.local_epochs is not None else None),
            participation=tp_cfg.participation,
            checkpoint_authorization=tp_cfg.checkpoint_authorization,
            personalization=tp_cfg.personalization,
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
    training_reg = TypedDomainRegistry(_items=training_dict)

    # 4. Resolve checkpoint profiles
    checkpoint_dict: dict[CheckpointProfileId, CheckpointProfileRecord] = {}
    for cp_key, cp_cfg in authored_protocols.checkpoint_profiles.items():
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
    checkpoint_reg = TypedDomainRegistry(_items=checkpoint_dict)

    # 5. Resolve seed cohorts
    seed_dict: dict[SeedCohortId, SeedCohortRecord] = {}
    for sc_key, sc_cfg in authored_protocols.seed_cohorts.items():
        sc_id = SeedCohortId(sc_key)
        seeds_tuple = tuple(Seed(int(s)) for s in sc_cfg.training_seeds)
        seed_dict[sc_id] = SeedCohortRecord(
            identifier=sc_id,
            paired_seed_count=PositiveInt(len(seeds_tuple)),
            training_seeds=seeds_tuple,
            bootstrap_analysis_seed=Seed(sc_cfg.bootstrap_analysis_seed),
            analysis_seed_model=sc_cfg.analysis_seed_model,
        )
    seed_reg = TypedDomainRegistry(_items=seed_dict)

    # 5b. Resolve the executable subset of statistical profiles.
    statistical_dict: dict[StatisticalProfileId, StatisticalProfileRecord] = {}
    for profile_key, profile_cfg in authored_protocols.statistical_profiles.items():
        minimum_units = (
            profile_cfg.minimum_paired_units
            if profile_cfg.minimum_paired_units is not None
            else profile_cfg.minimum_units
        )
        profile_id = StatisticalProfileId(profile_key)
        statistical_dict[profile_id] = StatisticalProfileRecord(
            identifier=profile_id,
            method=profile_cfg.method,
            confidence_level=(
                Probability(profile_cfg.confidence_level) if profile_cfg.confidence_level is not None else None
            ),
            resample_count=(
                PositiveInt(profile_cfg.resample_count) if profile_cfg.resample_count is not None else None
            ),
            minimum_units=PositiveInt(minimum_units) if minimum_units is not None else None,
        )
    statistical_reg = TypedDomainRegistry(_items=statistical_dict)

    # 6. Resolve threshold policies
    threshold_policies_dict: dict[ThresholdPolicyId, ThresholdPolicyRecord] = {}
    for tp_key, tp_cfg in authored_protocols.threshold_policies.items():
        tp_id = ThresholdPolicyId(tp_key)
        threshold_policies_dict[tp_id] = _resolve_threshold_policy(tp_cfg)

    # 7. Resolve experiments
    experiments_dict: dict[ExperimentId, ExperimentRecord] = {}
    for exp_cfg in authored_experiments.experiments:
        exp_id = ExperimentId(exp_cfg.name)
        if exp_id in experiments_dict:
            raise ConfigurationError(f"Duplicate experiment identifier: '{exp_cfg.name}'")

        # Validate evaluations threshold policies
        evals_list = []
        for ev in exp_cfg.evaluations:
            tp_id = ThresholdPolicyId(ev.threshold_policy)
            if tp_id not in threshold_policies_dict:
                raise ConfigurationError(
                    f"Experiment '{exp_cfg.name}' evaluation '{ev.label}' references "
                    f"unregistered threshold policy '{ev.threshold_policy}'"
                )
            evals_list.append(
                EvaluationSpecRecord(
                    label=ev.label,
                    threshold_policy_id=tp_id,
                    run_requirement=(
                        RunRequirement(ev.run_requirement) if ev.run_requirement else RunRequirement.MANDATORY
                    ),
                )
            )

        analyses_list = [
            AnalysisSpecRecord(
                label=a.label,
                kind=a.kind,
                result_type=a.result_type,
                primary_metric=a.primary_metric,
                statistical_profile=a.statistical_profile,
            )
            for a in exp_cfg.analyses
        ]

        experiments_dict[exp_id] = ExperimentRecord(
            identifier=exp_id,
            display_name=exp_cfg.display_name,
            evidence_role=EvidenceRole(exp_cfg.evidence_role),
            run_requirement=RunRequirement(exp_cfg.run_requirement),
            population_ids=tuple(PopulationId(p) for p in exp_cfg.populations),
            training_profile_id=TrainingProfileId(exp_cfg.training_profile),
            checkpoint_profile_id=CheckpointProfileId(exp_cfg.checkpoint_profile),
            seed_cohort_id=SeedCohortId(exp_cfg.seed_cohort),
            eligibility_policy_id=EligibilityPolicyId(exp_cfg.eligibility_policy),
            prerequisite_ids=tuple(ExperimentId(p.experiment) for p in exp_cfg.prerequisites),
            capability_requirements=tuple(
                CapabilityRequirementRecord(
                    capability=requirement.capability,
                    when_unavailable=requirement.when_unavailable,
                )
                for requirement in exp_cfg.capability_requirements
            ),
            evaluations=tuple(evals_list),
            analyses=tuple(analyses_list),
            report_ids=tuple(exp_cfg.reports),
            sweeps=(
                tuple(_resolve_sweep(name, sweep) for name, sweep in sorted(exp_cfg.sweeps.items()))
                if exp_cfg.sweeps is not None
                else ()
            ),
        )
    experiments_reg = TypedDomainRegistry(_items=experiments_dict)

    # Resolve protocol dictionaries
    model_architectures = {
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
        for key, m in authored_protocols.model_architectures.items()
    }
    optimizers = {
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
        for key, o in authored_protocols.optimizers.items()
    }
    batching_profiles = {
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
        for key, b in authored_protocols.batching.items()
    }
    eligibility_policies = {
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
        for k, v in authored_protocols.eligibility_policies.items()
    }
    normalization_strategies = {
        NormalizationStrategyId(k): NormalizationStrategyRecord(
            identifier=NormalizationStrategyId(k),
            formula=v.formula,
            fitted_statistics=tuple(v.fitted_statistics),
            constant_feature_rule=v.constant_feature_rule,
            out_of_range_transform_values=v.out_of_range_transform_values,
            fit_population=v.fit_population,
            standard_deviation_ddof=v.standard_deviation_ddof,
        )
        for k, v in authored_protocols.normalization_strategies.items()
    }
    quantile_estimators = {
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
        for k, v in authored_protocols.quantile_estimators.items()
    }
    metric_bundles = {
        MetricBundleId(k): MetricBundleRecord(
            identifier=MetricBundleId(k),
            metrics=tuple(v.metrics),
            cross_client_aggregation=v.cross_client_aggregation,
            primary_dispersion_metric=v.primary_dispersion_metric,
            model_quality_control=v.model_quality_control,
            excludes_ineligible_clients=v.excludes_ineligible_clients,
            requires_attack_evaluable_clients=v.requires_attack_evaluable_clients,
        )
        for k, v in authored_protocols.metric_bundles.items()
    }
    report_profiles = {key: _resolve_report_profile(key, v) for key, v in authored_protocols.report_profiles.items()}
    resolved_metric_definitions = _resolve_metric_definitions(authored_protocols.metric_definitions)
    resolved_artifact_identity = _resolve_artifact_identity(authored_protocols.artifact_identity)
    resolved_communication_estimation_contract = _resolve_communication_estimation_contract(
        authored_protocols.communication_estimation_contract
    )
    resolved_operational_inputs = _resolve_operational_inputs(authored_protocols.operational_inputs)
    resolved_communication_estimation = (
        cast(Mapping[str, object], deep_freeze(authored_protocols.communication_estimation))
        if authored_protocols.communication_estimation is not None
        else None
    )
    resolved_protocol_determinism = _resolve_protocol_determinism(authored_protocols.determinism)
    resolved_normalization_fit_scopes = MappingProxyType(dict(authored_protocols.normalization_fit_scopes))
    resolved_threshold_policy_defaults = _resolve_threshold_policy_defaults(
        authored_protocols.threshold_policy_defaults
    )
    resolved_nested_replicate_policy = _resolve_nested_replicate_policy(authored_protocols.nested_replicate_policy)
    result_types = {key: _resolve_result_type(key, v) for key, v in authored_protocols.result_types.items()}
    resolved_evaluation_result_contract = _resolve_evaluation_result_contract(
        authored_protocols.evaluation_result_contract
    )
    resolved_report_defaults = _resolve_report_defaults(authored_protocols.report_defaults)

    # Scientific fingerprint computation over full scientific content.
    # Absolute filesystem paths are deliberately excluded from identity (artifact_identity rule);
    # datasets are projected via their schema id, materialization contracts, and fingerprint field
    # lists rather than their resolved (absolute-path-bearing) record.
    scientific_projection: dict[str, object] = {
        "datasets": {
            str(k): {
                "schema_id": v.schema_id,
                "materializations": _unstructure(v.materializations),
                "fingerprint_source_fields": list(v.fingerprint_source_fields),
                "fingerprint_schema_fields": list(v.fingerprint_schema_fields),
                "fingerprint_materialization_fields": list(v.fingerprint_materialization_fields),
                "fingerprint_client_assignment_fields": list(v.fingerprint_client_assignment_fields),
            }
            for k, v in sorted(resolved_datasets.items(), key=lambda x: str(x[0]))
        },
        "populations": {str(k): _unstructure(v) for k, v in sorted(populations_dict.items(), key=lambda x: str(x[0]))},
        "experiments": {str(k): _unstructure(v) for k, v in sorted(experiments_dict.items(), key=lambda x: str(x[0]))},
        "threshold_policies": {
            str(k): _unstructure(v) for k, v in sorted(threshold_policies_dict.items(), key=lambda x: str(x[0]))
        },
        "seed_cohorts": {str(k): _unstructure(v) for k, v in sorted(seed_dict.items(), key=lambda x: str(x[0]))},
        "training_profiles": {
            str(k): _unstructure(v) for k, v in sorted(training_dict.items(), key=lambda x: str(x[0]))
        },
        "checkpoint_profiles": {
            str(k): _unstructure(v) for k, v in sorted(checkpoint_dict.items(), key=lambda x: str(x[0]))
        },
        "model_architectures": {k: _unstructure(v) for k, v in sorted(model_architectures.items())},
        "optimizers": {k: _unstructure(v) for k, v in sorted(optimizers.items())},
        "batching": {k: _unstructure(v) for k, v in sorted(batching_profiles.items())},
        "eligibility_policies": {
            str(k): _unstructure(v) for k, v in sorted(eligibility_policies.items(), key=lambda x: str(x[0]))
        },
        "normalization_strategies": {
            str(k): _unstructure(v) for k, v in sorted(normalization_strategies.items(), key=lambda x: str(x[0]))
        },
        "quantile_estimators": {k: _unstructure(v) for k, v in sorted(quantile_estimators.items())},
        "metric_bundles": {str(k): _unstructure(v) for k, v in sorted(metric_bundles.items(), key=lambda x: str(x[0]))},
        "statistical_profiles": {
            str(k): _unstructure(v) for k, v in sorted(statistical_dict.items(), key=lambda x: str(x[0]))
        },
        "metric_definitions": _unstructure(resolved_metric_definitions),
        "artifact_identity": _unstructure(resolved_artifact_identity),
        "communication_estimation_contract": _unstructure(resolved_communication_estimation_contract),
        "operational_inputs": _unstructure(resolved_operational_inputs),
        "report_profiles": {k: _unstructure(v) for k, v in sorted(report_profiles.items())},
        "communication_estimation": _unstructure(resolved_communication_estimation),
        "protocol_determinism": _unstructure(resolved_protocol_determinism),
        "normalization_fit_scopes": dict(sorted(resolved_normalization_fit_scopes.items())),
        "normalization_leakage_rule": authored_protocols.normalization_leakage_rule,
        "threshold_policy_defaults": _unstructure(resolved_threshold_policy_defaults),
        "nested_replicate_policy": _unstructure(resolved_nested_replicate_policy),
        "result_types": {k: _unstructure(v) for k, v in sorted(result_types.items())},
        "evaluation_result_contract": _unstructure(resolved_evaluation_result_contract),
        "report_defaults": _unstructure(resolved_report_defaults),
    }
    scientific_fingerprint = compute_scientific_fingerprint(scientific_projection)

    execution_projection = {
        "scientific_fingerprint": scientific_fingerprint.value,
        "active_execution_profile": _unstructure(resolved_runtime.active_execution_profile),
        "determinism": _unstructure(resolved_runtime.determinism_enforcement),
        "device_policy": _unstructure(resolved_runtime.device_policy_rules),
        "resource_pressure": _unstructure(resolved_runtime.resource_pressure_policy),
        "raw_source_policy": _unstructure(resolved_runtime.raw_source_policy),
    }
    execution_fingerprint = compute_execution_fingerprint(execution_projection)
    canonical_scientific_projection = canonicalize_value(scientific_projection)
    canonical_execution_projection = canonicalize_value(execution_projection)

    return ResolvedProjectConfiguration(
        datasets=TypedDomainRegistry(_items=resolved_datasets),
        populations=populations_reg,
        experiments=experiments_reg,
        training_profiles=training_reg,
        checkpoint_profiles=checkpoint_reg,
        seed_cohorts=seed_reg,
        statistical_profiles=statistical_reg,
        threshold_policies=TypedDomainRegistry(_items=threshold_policies_dict),
        model_architectures=TypedDomainRegistry(_items=model_architectures),
        optimizers=TypedDomainRegistry(_items=optimizers),
        batching_profiles=TypedDomainRegistry(_items=batching_profiles),
        eligibility_policies=TypedDomainRegistry(_items=eligibility_policies),
        normalization_strategies=TypedDomainRegistry(_items=normalization_strategies),
        quantile_estimators=TypedDomainRegistry(_items=quantile_estimators),
        metric_bundles=TypedDomainRegistry(_items=metric_bundles),
        metric_definitions=resolved_metric_definitions,
        artifact_identity=resolved_artifact_identity,
        communication_estimation_contract=resolved_communication_estimation_contract,
        operational_inputs=resolved_operational_inputs,
        report_profiles=TypedDomainRegistry(_items=report_profiles),
        communication_estimation=resolved_communication_estimation,
        protocol_determinism=resolved_protocol_determinism,
        normalization_fit_scopes=resolved_normalization_fit_scopes,
        normalization_leakage_rule=authored_protocols.normalization_leakage_rule,
        threshold_policy_defaults=resolved_threshold_policy_defaults,
        nested_replicate_policy=resolved_nested_replicate_policy,
        result_types=TypedDomainRegistry(_items=result_types),
        evaluation_result_contract=resolved_evaluation_result_contract,
        report_defaults=resolved_report_defaults,
        runtime=resolved_runtime,
        paths=paths,
        scientific_fingerprint=scientific_fingerprint,
        execution_fingerprint=execution_fingerprint,
        scientific_projection=canonical_scientific_projection,
        execution_projection=canonical_execution_projection,
    )
