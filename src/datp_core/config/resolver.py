"""Staged resolution pipeline converting authored YAML documents into an immutable ResolvedProjectConfiguration."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import cast

import cattrs
from attrs import define

from datp_core.config.models.dataset_config import (
    CategoricalEncodingConfig,
    DatasetFieldSchemaConfig,
    DatasetSourceLayoutConfig,
    EndpointIdentityConfig,
    IdentitySchemeConfig,
    LabelFieldsConfig,
    SetupClientConstructionConfig,
    SourceContractConfig,
)
from datp_core.config.models.experiment_config import AnalysisSpecConfig, AuthoredExperimentConfig, SweepVariableConfig
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
    AbsorptionAnalysisRecord,
    AlertBurdenAnalysisRecord,
    AnalysisRecord,
    AnchorEquivalenceAnalysisRecord,
    BatchingRecord,
    CalibrationSubsetRecord,
    CapabilityRequirementRecord,
    CheckpointConvergenceRecord,
    CheckpointProfileRecord,
    CheckpointSelectionRecord,
    ClusterStabilityAnalysisRecord,
    ConditionSweepRecord,
    ConformalCoverageAnalysisRecord,
    DistributionMechanismAnalysisRecord,
    EligibilityFallbackRecord,
    EligibilityGateRecord,
    EligibilityPolicyRecord,
    EvaluationSpecRecord,
    EvidenceRole,
    ExperimentRecord,
    FederationProfileRecord,
    LockedClientDistributionAnalysisRecord,
    MetricAssociationAnalysisRecord,
    MetricBundleRecord,
    ModelArchitectureRecord,
    NormalizationStrategyRecord,
    OptimizerRecord,
    PairedThresholdAnalysisRecord,
    PopulationRecord,
    PrerequisiteSpecRecord,
    QuantileEstimationAnalysisRecord,
    QuantileEstimatorRecord,
    RecoveryFractionAnalysisRecord,
    ResourceCostAnalysisRecord,
    RunRequirement,
    SeedCohortRecord,
    StatisticalProfileRecord,
    SweepConditionRecord,
    SweepRecord,
    SweepValue,
    TemporalRecoveryAnalysisRecord,
    ThresholdStabilityAnalysisRecord,
    TrainingProfileRecord,
    ValueSweepRecord,
)
from datp_core.domain.datasets import (
    AdapterKind,
    CategoricalEncodingRecord,
    ConfiguredSourceTree,
    CrossSourceRelationshipRecord,
    DatasetFieldSchemaRecord,
    DatasetInspectionContract,
    DatasetMaterialization,
    DatasetSetup,
    DatasetSourceLayoutContractRecord,
    DatasetSourceRecord,
    EndpointIdentityRecord,
    IdentitySchemeRecord,
    LabelFieldsRecord,
    ModelFeaturesRecord,
    MulticlassLabelRecord,
    ResolvedDataset,
    ResolvedDatasetPaths,
    RetainedNumericFeaturesRecord,
    SetupClientConstructionRecord,
    SourceContractRecord,
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
    as_optional_frozen_json_mapping,
    deep_freeze,
)

_projection_converter = cattrs.Converter()


def _unstructure(value: object) -> object:
    """Convert resolved attrs records into primitive structures for canonical fingerprinting."""
    return _projection_converter.unstructure(value)


def _experiment_scientific_projection(record: ExperimentRecord) -> dict[str, object]:
    """Unstructure an experiment for the scientific fingerprint, excluding display-only prose.

    `display_name` is authored human-readable prose with no bearing on what is executed, evaluated,
    or claimed; it is the one field in `AuthoredExperimentConfig` classified AUTHORING_METADATA.
    """
    projected = cast(dict, _unstructure(record))
    del projected["display_name"]
    return projected


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


def _require(value: object | None, *, experiment_name: str, analysis_label: str, field_name: str) -> object:
    if value is None:
        raise ConfigurationError(
            f"Experiment '{experiment_name}' analysis '{analysis_label}' is missing required field '{field_name}'"
        )
    return value


def _resolve_analysis(exp_cfg: AuthoredExperimentConfig, a: AnalysisSpecConfig) -> AnalysisRecord:
    def req(field_name: str) -> object:
        return _require(
            getattr(a, field_name), experiment_name=exp_cfg.name, analysis_label=a.label, field_name=field_name
        )

    statistical_profile = StatisticalProfileId(cast(str, req("statistical_profile")))
    secondary_statistical_profile = (
        StatisticalProfileId(a.secondary_statistical_profile) if a.secondary_statistical_profile is not None else None
    )

    if a.kind == "paired_threshold_analysis":
        return PairedThresholdAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            secondary_statistical_profile=secondary_statistical_profile,
            first_evaluation=cast(str, req("first_evaluation")),
            second_evaluation=cast(str, req("second_evaluation")),
            primary_metric=cast(str, req("primary_metric")),
            delta_orientation=cast(str, req("delta_orientation")),
            delta_interpretation=cast(str, req("delta_interpretation")),
            required_direction=a.required_direction,
            monotonicity_required=a.monotonicity_required,
            ordering_inversion_reporting=a.ordering_inversion_reporting,
            per_sweep_cell=a.per_sweep_cell,
            full_curve_reporting=a.full_curve_reporting,
            post_hoc_weight_selection=a.post_hoc_weight_selection,
        )
    if a.kind == "absorption_analysis":
        return AbsorptionAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            absorption_metric=cast(str, req("absorption_metric")),
            formula=cast(str, req("formula")),
            band_interpretation=cast(str, req("band_interpretation")),
            denominator_materiality_rule=cast("float | str", req("denominator_materiality_rule")),
            undefined_denominator_behavior=cast(str, req("undefined_denominator_behavior")),
            matching_contract=cast(dict, req("matching_contract")),
            outcome_bands=cast(list, req("outcome_bands")),
            outcome_bands_are_mutually_exclusive_and_exhaustive=cast(
                bool, req("outcome_bands_are_mutually_exclusive_and_exhaustive")
            ),
            reference_analysis=cast("str | dict", req("reference_analysis")),
            stress_test_analysis=cast(str, req("stress_test_analysis")),
            alternative_path_rule=a.alternative_path_rule,
        )
    if a.kind == "alert_burden_analysis":
        return AlertBurdenAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            formula=cast(str, req("formula")),
            produced_fields=tuple(cast("list[str]", req("produced_fields"))),
            source_evaluations=tuple(cast("list[str]", req("source_evaluations"))),
            required_operational_input=cast(str, req("required_operational_input")),
            per_client_reporting_required=cast(bool, req("per_client_reporting_required")),
            unavailable_behavior=cast(str, req("unavailable_behavior")),
        )
    if a.kind == "anchor_equivalence_analysis":
        return AnchorEquivalenceAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_analysis=cast(str, req("source_analysis")),
            comparison_mode=cast(str, req("comparison_mode")),
            comparison_mode_rule=cast(str, req("comparison_mode_rule")),
            interval_width_tolerance_multiplier=cast(float, req("interval_width_tolerance_multiplier")),
            floating_point_tolerance=cast("dict[str, float]", req("floating_point_tolerance")),
            historical_reference=cast("dict[str, float | str]", req("historical_reference")),
            statistical_fallback_requirements=tuple(cast("list[str]", req("statistical_fallback_requirements"))),
            failure_reasons=tuple(cast("list[str]", req("failure_reasons"))),
            downstream_blocking_behavior=cast(str, req("downstream_blocking_behavior")),
        )
    if a.kind == "cluster_stability_analysis":
        return ClusterStabilityAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluation=cast(str, req("source_evaluation")),
            comparison_unit=cast(str, req("comparison_unit")),
            produced_fields=tuple(cast("list[str]", req("produced_fields"))),
            reference_evaluation=a.reference_evaluation,
            run_requirement=(RunRequirement(a.run_requirement) if a.run_requirement is not None else None),
        )
    if a.kind == "conformal_coverage_analysis":
        return ConformalCoverageAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluation=cast(str, req("source_evaluation")),
            target_coverage=cast(float, req("target_coverage")),
            produced_fields=tuple(cast("list[str]", req("produced_fields"))),
            coverage_direction=a.coverage_direction,
        )
    if a.kind == "distribution_mechanism_analysis":
        return DistributionMechanismAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluations=tuple(cast("list[str]", req("source_evaluations"))),
            produced_fields=tuple(cast("list[str]", req("produced_fields"))),
            field_formulas=a.field_formulas,
        )
    if a.kind == "locked_client_distribution_analysis":
        return LockedClientDistributionAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluations=tuple(cast("list[str]", req("source_evaluations"))),
            produced_fields=tuple(cast("list[str]", req("produced_fields"))),
            locked_client_identifier=cast(str, req("locked_client_identifier")),
        )
    if a.kind == "metric_association_analysis":
        return MetricAssociationAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            secondary_statistical_profile=secondary_statistical_profile,
            predictor_metric=cast(str, req("predictor_metric")),
            outcome_metric=cast(str, req("outcome_metric")),
            outcome_source_analysis=cast(str, req("outcome_source_analysis")),
            interpretation_constraint=cast(str, req("interpretation_constraint")),
            grouping_dimension=a.grouping_dimension,
        )
    if a.kind == "quantile_estimation_analysis":
        return QuantileEstimationAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluations=tuple(cast("list[str]", req("source_evaluations"))),
            produced_fields=tuple(cast("list[str]", req("produced_fields"))),
            oracle_reference=cast(str, req("oracle_reference")),
        )
    if a.kind == "recovery_fraction_analysis":
        return RecoveryFractionAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            formula=cast(str, req("formula")),
            numerator_analysis=cast(str, req("numerator_analysis")),
            denominator_analysis=cast(str, req("denominator_analysis")),
            denominator_composition=cast(str, req("denominator_composition")),
            denominator_materiality_rule=cast("float | str", req("denominator_materiality_rule")),
            undefined_denominator_behavior=cast(str, req("undefined_denominator_behavior")),
        )
    if a.kind == "resource_cost_analysis":
        return ResourceCostAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluations=tuple(cast("list[str]", req("source_evaluations"))),
            produced_fields=tuple(cast("list[str]", req("produced_fields"))),
            estimate_basis=cast(str, req("estimate_basis")),
        )
    if a.kind == "temporal_recovery_analysis":
        return TemporalRecoveryAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            primary_metric=cast(str, req("primary_metric")),
            static_reference_evaluation=cast(str, req("static_reference_evaluation")),
            frozen_evaluation=cast(str, req("frozen_evaluation")),
            recalibrated_evaluation=cast(str, req("recalibrated_evaluation")),
            recovery_fields=tuple(cast("list[str]", req("recovery_fields"))),
            drift_excess_formula=cast(str, req("drift_excess_formula")),
            recovered_amount_formula=cast(str, req("recovered_amount_formula")),
            recovery_ratio_formula=cast(str, req("recovery_ratio_formula")),
            meaningful_degradation_rule=cast(str, req("meaningful_degradation_rule")),
            recovery_ratio_precondition=cast(str, req("recovery_ratio_precondition")),
            negative_recovery_policy=cast(str, req("negative_recovery_policy")),
            recovery_ratio_direction=cast(str, req("recovery_ratio_direction")),
            chronology_unverifiable_policy=cast(str, req("chronology_unverifiable_policy")),
            outcome_bands=cast(list, req("outcome_bands")),
            outcome_bands_are_mutually_exclusive_and_exhaustive=cast(
                bool, req("outcome_bands_are_mutually_exclusive_and_exhaustive")
            ),
        )
    if a.kind == "threshold_stability_analysis":
        return ThresholdStabilityAnalysisRecord(
            label=a.label,
            kind=a.kind,
            result_type=a.result_type,
            statistical_profile=statistical_profile,
            source_evaluation=cast(str, req("source_evaluation")),
            produced_fields=tuple(cast("list[str]", req("produced_fields"))),
            per_sweep_cell=cast(str, req("per_sweep_cell")),
        )
    raise ConfigurationError(f"Experiment '{exp_cfg.name}' analysis '{a.label}' has unsupported kind '{a.kind}'")


@define(frozen=True, slots=True, kw_only=True)
class ResolvedProjectConfiguration:
    """Single resolved project configuration authority loaded once during composition root initialization."""

    datasets: TypedDomainRegistry[DatasetId, ResolvedDataset]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    capabilities: tuple[str, ...]
    suppression_behaviors: tuple[str, ...]
    population_readiness_rule: Mapping[str, str | bool]
    eligibility_gates: TypedDomainRegistry[str, EligibilityGateRecord]
    analysis_conventions: Mapping[str, str]
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


def _resolve_identity_scheme(cfg: IdentitySchemeConfig) -> IdentitySchemeRecord:
    return IdentitySchemeRecord(
        row_identity=cfg.row_identity,
        client_identity=cfg.client_identity,
        benign_group_identity=cfg.benign_group_identity,
        attack_row_group_identity=cfg.attack_row_group_identity,
        label_identity=cfg.label_identity,
        attack_family_identity=cfg.attack_family_identity,
        attack_type_identity=cfg.attack_type_identity,
        device_identity=cfg.device_identity,
        device_mac_ip_field=cfg.device_mac_ip_field,
        timestamp_field=cfg.timestamp_field,
        chronological_ordering_basis=cfg.chronological_ordering_basis,
        provenance_fields=tuple(cfg.provenance_fields),
    )


def _resolve_label_fields(cfg: LabelFieldsConfig) -> LabelFieldsRecord:
    multiclass = cfg.multiclass_label
    return LabelFieldsRecord(
        binary_label=cfg.binary_label,
        multiclass_label=(
            MulticlassLabelRecord(column=multiclass.column, type=multiclass.type, case=multiclass.case)
            if multiclass is not None
            else None
        ),
        benign_value=cfg.benign_value,
        attack_class_mapping=cfg.attack_class_mapping,
        device_family_mapping=cfg.device_family_mapping,
        family_taxonomy=cfg.family_taxonomy,
        family_map=cfg.family_map,
    )


def _resolve_endpoint_identity(cfg: EndpointIdentityConfig) -> EndpointIdentityRecord:
    return EndpointIdentityRecord(
        resolution=cfg.resolution,
        fields=tuple(cfg.fields),
        internal_prefix=cfg.internal_prefix,
        subnet_component=cfg.subnet_component,
        subnet_role_source=cfg.subnet_role_source,
        subnet_to_group=cfg.subnet_to_group,
        excluded_endpoints=cfg.excluded_endpoints,
        direction_normalization=cfg.direction_normalization,
        use=cfg.use,
        unresolved_row_policy=cfg.unresolved_row_policy,
    )


def _resolve_categorical_encoding(cfg: CategoricalEncodingConfig) -> CategoricalEncodingRecord:
    return CategoricalEncodingRecord(
        strategy=cfg.strategy,
        columns=tuple(cfg.columns),
        vocabulary_scope=cfg.vocabulary_scope,
        vocabulary_artifact=cfg.vocabulary_artifact,
        vocabulary_fingerprint=cfg.vocabulary_fingerprint,
        category_order=cfg.category_order,
        encoded_feature_naming=cfg.encoded_feature_naming,
        missing_category_policy=cfg.missing_category_policy,
        unknown_category_policy=cfg.unknown_category_policy,
        unknown_indicator_distinct_from_missing_indicator=cfg.unknown_indicator_distinct_from_missing_indicator,
        feature_order=tuple(cfg.feature_order),
    )


def _resolve_field_schema(cfg: DatasetFieldSchemaConfig) -> DatasetFieldSchemaRecord:
    model_features = cfg.model_features
    retained_numeric_features = cfg.retained_numeric_features
    endpoint_identity = cfg.endpoint_identity
    return DatasetFieldSchemaRecord(
        source_column_count=cfg.source_column_count,
        header_required=cfg.header_required,
        header_must_be_identical_across_all_source_files=cfg.header_must_be_identical_across_all_source_files,
        header_must_be_identical_across_all_files_in_a_tree=cfg.header_must_be_identical_across_all_files_in_a_tree,
        merged_header_extends_per_class_header_with=cfg.merged_header_extends_per_class_header_with,
        label_column_position=cfg.label_column_position,
        identity_scheme=_resolve_identity_scheme(cfg.identity_scheme),
        label_fields=_resolve_label_fields(cfg.label_fields),
        model_features=(
            ModelFeaturesRecord(role=model_features.role, type=model_features.type, order=tuple(model_features.order))
            if model_features is not None
            else None
        ),
        source_columns=tuple(cfg.source_columns) if cfg.source_columns is not None else None,
        endpoint_identity=(_resolve_endpoint_identity(endpoint_identity) if endpoint_identity is not None else None),
        attack_row_group_policy=cfg.attack_row_group_policy,
        retained_numeric_features=(
            RetainedNumericFeaturesRecord(
                role=retained_numeric_features.role,
                order=tuple(retained_numeric_features.order),
                numeric_parsing=retained_numeric_features.numeric_parsing,
                on_invalid_value=retained_numeric_features.on_invalid_value,
            )
            if retained_numeric_features is not None
            else None
        ),
        post_encoding_feature_order=cfg.post_encoding_feature_order,
        categorical_encoding=(
            cfg.categorical_encoding
            if isinstance(cfg.categorical_encoding, str)
            else _resolve_categorical_encoding(cfg.categorical_encoding)
        ),
        leakage_exclusions=cfg.leakage_exclusions,
    )


def _resolve_source_layout_contract(cfg: DatasetSourceLayoutConfig) -> DatasetSourceLayoutContractRecord:
    cross_source_relationship = cfg.cross_source_relationship
    return DatasetSourceLayoutContractRecord(
        root=RelativePath(cfg.root),
        benign_file=cfg.benign_file,
        benign_file_pattern=cfg.benign_file_pattern,
        normal_file_pattern=cfg.normal_file_pattern,
        attack_file_pattern=cfg.attack_file_pattern,
        device_dirs=tuple(cfg.device_dirs) if cfg.device_dirs is not None else None,
        normal_group_folders=tuple(cfg.normal_group_folders) if cfg.normal_group_folders is not None else None,
        executable_group_folders=(
            tuple(cfg.executable_group_folders) if cfg.executable_group_folders is not None else None
        ),
        attack_files=tuple(cfg.attack_files) if cfg.attack_files is not None else None,
        ignored_source_suffixes=tuple(cfg.ignored_source_suffixes),
        ignored_root_entries=tuple(cfg.ignored_root_entries),
        ignored_subtrees=tuple(cfg.ignored_subtrees),
        sources=(
            {
                key: DatasetSourceRecord(
                    role=source.role,
                    root=RelativePath(source.root),
                    file_pattern=source.file_pattern,
                    owns=tuple(source.owns) if source.owns is not None else None,
                    permitted_uses=tuple(source.permitted_uses) if source.permitted_uses is not None else None,
                    contributes_rows_to_executable_materializations=(
                        source.contributes_rows_to_executable_materializations
                    ),
                    defines_pseudo_clients=source.defines_pseudo_clients,
                )
                for key, source in cfg.sources.items()
            }
            if cfg.sources is not None
            else None
        ),
        executable_source=cfg.executable_source,
        cross_source_relationship=(
            CrossSourceRelationshipRecord(
                row_count_equality_required=cross_source_relationship.row_count_equality_required,
                row_level_one_to_one_equivalence_assumed=(
                    cross_source_relationship.row_level_one_to_one_equivalence_assumed
                ),
                join_by_row_position=cross_source_relationship.join_by_row_position,
                join_by_any_key=cross_source_relationship.join_by_any_key,
            )
            if cross_source_relationship is not None
            else None
        ),
        normal_traffic_root=(RelativePath(cfg.normal_traffic_root) if cfg.normal_traffic_root is not None else None),
        attack_traffic_root=(RelativePath(cfg.attack_traffic_root) if cfg.attack_traffic_root is not None else None),
        benign_file_required_per_device=cfg.benign_file_required_per_device,
        attack_family_dirs=tuple(cfg.attack_family_dirs) if cfg.attack_family_dirs is not None else None,
        attack_family_required_per_device=cfg.attack_family_required_per_device,
    )


def _resolve_source_contract(cfg: SourceContractConfig) -> SourceContractRecord:
    return SourceContractRecord(
        every_model_feature_present_in_merged_header=cfg.every_model_feature_present_in_merged_header,
        every_model_feature_present_in_every_file=cfg.every_model_feature_present_in_every_file,
        model_feature_count_equals_source_column_count=cfg.model_feature_count_equals_source_column_count,
        per_class_schema_reference_check=cfg.per_class_schema_reference_check,
        malformed_row=cfg.malformed_row,
        empty_label_row=cfg.empty_label_row,
        reject_unparseable_numeric_model_feature=cfg.reject_unparseable_numeric_model_feature,
        reject_row_with_field_count_other_than_header=cfg.reject_row_with_field_count_other_than_header,
        column_role_partition=cfg.column_role_partition,
        positional_contract=cfg.positional_contract,
        row_integrity_exclusions=cfg.row_integrity_exclusions,
    )


def _resolve_client_construction(cfg: SetupClientConstructionConfig) -> SetupClientConstructionRecord:
    client_source: str | tuple[str, ...] | None
    if cfg.client_source is None or isinstance(cfg.client_source, str):
        client_source = cfg.client_source
    else:
        client_source = tuple(cfg.client_source)
    return SetupClientConstructionRecord(
        method=cfg.method,
        client_source=client_source,
        client_semantics=cfg.client_semantics,
        excluded_client_folders=(
            tuple(cfg.excluded_client_folders) if cfg.excluded_client_folders is not None else None
        ),
        client_count=PositiveInt(cfg.client_count) if cfg.client_count is not None else None,
        partition_condition=cfg.partition_condition,
        source_mixture_components=cfg.source_mixture_components,
        label_field=cfg.label_field,
        partition_seed=Seed(cfg.partition_seed) if cfg.partition_seed is not None else None,
        partition_axes=cfg.partition_axes,
        allocation_procedure=cfg.allocation_procedure,
        same_proportions_govern=(
            tuple(cfg.same_proportions_govern) if cfg.same_proportions_govern is not None else None
        ),
        split_role_preservation=cfg.split_role_preservation,
        attack_row_assignment=cfg.attack_row_assignment,
        attack_labels_used_in_partition_generation=cfg.attack_labels_used_in_partition_generation,
        minimum_row_counts=cfg.minimum_row_counts,
        retry_policy=cfg.retry_policy,
        feasibility_failure=cfg.feasibility_failure,
        manifest_invariants=(tuple(cfg.manifest_invariants) if cfg.manifest_invariants is not None else None),
        manifest_fields=(tuple(cfg.manifest_fields) if cfg.manifest_fields is not None else None),
    )


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
        setup_identifiers = set(d_cfg.setups)
        setups_list = []
        for identifier, setup in sorted(d_cfg.setups.items()):
            if (
                setup.client_population_must_equal_setup is not None
                and setup.client_population_must_equal_setup not in setup_identifiers
            ):
                raise ConfigurationError(
                    f"Dataset '{d_cfg.dataset}' setup '{identifier}' references unregistered "
                    f"client_population_must_equal_setup '{setup.client_population_must_equal_setup}'"
                )
            setups_list.append(
                DatasetSetup(
                    identifier=DatasetSetupId(identifier),
                    materialization_id=MaterializationId(setup.materialization),
                    capabilities=tuple(setup.provides_capabilities),
                    client_construction=_resolve_client_construction(setup.client_construction),
                    validation_scope=setup.validation_scope,
                    eligibility_gate=setup.eligibility_gate,
                    client_population_must_equal_setup=(
                        DatasetSetupId(setup.client_population_must_equal_setup)
                        if setup.client_population_must_equal_setup is not None
                        else None
                    ),
                )
            )
        setups = tuple(setups_list)
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
                split_minimum_row_counts=materialization.split.minimum_row_counts,
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
            source_layout_contract=_resolve_source_layout_contract(d_cfg.source_layout),
            field_schema=_resolve_field_schema(d_cfg.field_schema),
            source_contract=_resolve_source_contract(d_cfg.source_contract),
            client_identity_contract=(
                as_optional_frozen_json_mapping(d_cfg.client_identity_contract)
                if d_cfg.client_identity_contract is not None
                else None
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

    # 2b. Resolve catalogue-level contracts (capabilities, suppression, readiness, eligibility gates, conventions)
    eligibility_gates_dict: dict[str, EligibilityGateRecord] = {}
    for gate_key, gate_cfg in authored_experiments.eligibility_gates.items():
        eligibility_gates_dict[gate_key] = EligibilityGateRecord(
            identifier=gate_key,
            candidate_population=gate_cfg.candidate_population,
            minimum_benign_calibration_count=PositiveInt(gate_cfg.minimum_benign_calibration_count),
            minimum_eligible_client_proportion=Probability(gate_cfg.minimum_eligible_client_proportion),
            evaluation_time=gate_cfg.evaluation_time,
            failure_outcome=gate_cfg.failure_outcome,
            population_reduction_without_explicit_roadmap_authorization=(
                gate_cfg.population_reduction_without_explicit_roadmap_authorization
            ),
            applies_to_experiments=tuple(ExperimentId(e) for e in gate_cfg.applies_to_experiments),
        )
    eligibility_gates_reg = TypedDomainRegistry(_items=eligibility_gates_dict)
    catalogue_capabilities = tuple(authored_experiments.capabilities)
    catalogue_suppression_behaviors = tuple(authored_experiments.suppression_behaviors)
    catalogue_population_readiness_rule = MappingProxyType(dict(authored_experiments.population_readiness_rule))
    catalogue_analysis_conventions = MappingProxyType(dict(authored_experiments.analysis_conventions))

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

        # Validate evaluations threshold policies and populations
        evals_list = []
        for ev in exp_cfg.evaluations:
            tp_id = ThresholdPolicyId(ev.threshold_policy)
            if tp_id not in threshold_policies_dict:
                raise ConfigurationError(
                    f"Experiment '{exp_cfg.name}' evaluation '{ev.label}' references "
                    f"unregistered threshold policy '{ev.threshold_policy}'"
                )
            eval_population_id = PopulationId(ev.population) if ev.population is not None else None
            if eval_population_id is not None and eval_population_id not in populations_dict:
                raise ConfigurationError(
                    f"Experiment '{exp_cfg.name}' evaluation '{ev.label}' references "
                    f"unregistered population '{ev.population}'"
                )
            evals_list.append(
                EvaluationSpecRecord(
                    label=ev.label,
                    threshold_policy_id=tp_id,
                    run_requirement=(
                        RunRequirement(ev.run_requirement) if ev.run_requirement else RunRequirement.MANDATORY
                    ),
                    overrides=ev.overrides,
                    population_id=eval_population_id,
                    recalibration_mode=ev.recalibration_mode,
                )
            )

        analyses_list = [_resolve_analysis(exp_cfg, a) for a in exp_cfg.analyses]

        capability_requirements_list = []
        for requirement in exp_cfg.capability_requirements:
            applies_to_population_ids = (
                tuple(PopulationId(p) for p in requirement.applies_to_populations)
                if requirement.applies_to_populations is not None
                else None
            )
            if applies_to_population_ids is not None:
                for pop_id in applies_to_population_ids:
                    if pop_id not in populations_dict:
                        raise ConfigurationError(
                            f"Experiment '{exp_cfg.name}' capability requirement '{requirement.capability}' "
                            f"references unregistered population '{pop_id}'"
                        )
            capability_requirements_list.append(
                CapabilityRequirementRecord(
                    capability=requirement.capability,
                    when_unavailable=requirement.when_unavailable,
                    applies_to_populations=applies_to_population_ids,
                )
            )

        calibration_subset_record = (
            CalibrationSubsetRecord(
                requested_sample_count=exp_cfg.calibration_subset.requested_sample_count,
                selection_strategy=exp_cfg.calibration_subset.selection_strategy,
                nesting_policy=exp_cfg.calibration_subset.nesting_policy,
                nesting_rule=exp_cfg.calibration_subset.nesting_rule,
                selection_seed=Seed(exp_cfg.calibration_subset.selection_seed),
                replicate_count=PositiveInt(exp_cfg.calibration_subset.replicate_count),
                replicate_seed_derivation=exp_cfg.calibration_subset.replicate_seed_derivation,
                model_retraining=exp_cfg.calibration_subset.model_retraining,
                client_eligibility_per_requested_size=exp_cfg.calibration_subset.client_eligibility_per_requested_size,
                subminimum_eligibility_policy=exp_cfg.calibration_subset.subminimum_eligibility_policy,
                subminimum_eligibility_policy_applies_to=(
                    exp_cfg.calibration_subset.subminimum_eligibility_policy_applies_to
                ),
                effective_eligibility_policy_by_sweep_condition=(
                    exp_cfg.calibration_subset.effective_eligibility_policy_by_sweep_condition
                ),
                insufficient_row_policy=exp_cfg.calibration_subset.insufficient_row_policy,
                replicate_aggregation_within_seed=exp_cfg.calibration_subset.replicate_aggregation_within_seed,
                seed_level_statistic=exp_cfg.calibration_subset.seed_level_statistic,
                additional_seed_level_statistic=exp_cfg.calibration_subset.additional_seed_level_statistic,
                independent_inferential_unit=exp_cfg.calibration_subset.independent_inferential_unit,
                replicates_counted_as_seeds=exp_cfg.calibration_subset.replicates_counted_as_seeds,
                full_calibration_reference_condition=exp_cfg.calibration_subset.full_calibration_reference_condition,
            )
            if exp_cfg.calibration_subset is not None
            else None
        )

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
            prerequisites=tuple(
                PrerequisiteSpecRecord(experiment_id=ExperimentId(p.experiment), required_outcome=p.required_outcome)
                for p in exp_cfg.prerequisites
            ),
            capability_requirements=tuple(capability_requirements_list),
            evaluations=tuple(evals_list),
            analyses=tuple(analyses_list),
            report_ids=tuple(exp_cfg.reports),
            sweeps=(
                tuple(_resolve_sweep(name, sweep) for name, sweep in sorted(exp_cfg.sweeps.items()))
                if exp_cfg.sweeps is not None
                else ()
            ),
            readiness_gates=tuple(exp_cfg.readiness_gates),
            validation_scope=exp_cfg.validation_scope,
            never_promoted_to_confirmatory=exp_cfg.never_promoted_to_confirmatory,
            outside_core_causal_ladder=exp_cfg.outside_core_causal_ladder,
            faithful_reproduction_claim_forbidden=exp_cfg.faithful_reproduction_claim_forbidden,
            attack_sensitive_metrics_requested=exp_cfg.attack_sensitive_metrics_requested,
            unavailable_capability_reporting=tuple(exp_cfg.unavailable_capability_reporting),
            independent_of_experiment=(
                ExperimentId(exp_cfg.independent_of_experiment)
                if exp_cfg.independent_of_experiment is not None
                else None
            ),
            calibration_subset=calibration_subset_record,
            method_naming_rule=exp_cfg.method_naming_rule,
            personalization_parameter_selection_source=exp_cfg.personalization_parameter_selection_source,
            run_condition=exp_cfg.run_condition,
            unavailable_behavior=exp_cfg.unavailable_behavior,
            blocks_other_experiments_when_unavailable=exp_cfg.blocks_other_experiments_when_unavailable,
            estimate_basis=exp_cfg.estimate_basis,
            client_semantics_constraint=exp_cfg.client_semantics_constraint,
            generalization_constraint=exp_cfg.generalization_constraint,
            quantitative_claim_gate=exp_cfg.quantitative_claim_gate,
            population_equivalence_requirement=exp_cfg.population_equivalence_requirement,
            population_roles=exp_cfg.population_roles,
            scope_constraint=exp_cfg.scope_constraint,
            temporal_procedure=exp_cfg.temporal_procedure,
            primary_coefficient_selection=exp_cfg.primary_coefficient_selection,
            training_overrides=exp_cfg.training_overrides,
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
                "source_layout_contract": _unstructure(v.source_layout_contract),
                "field_schema": _unstructure(v.field_schema),
                "source_contract": _unstructure(v.source_contract),
                "client_identity_contract": _unstructure(v.client_identity_contract),
                "setups": _unstructure(v.setups),
                "materializations": _unstructure(v.materializations),
                "capabilities": list(v.capabilities),
                "fingerprint_source_fields": list(v.fingerprint_source_fields),
                "fingerprint_schema_fields": list(v.fingerprint_schema_fields),
                "fingerprint_materialization_fields": list(v.fingerprint_materialization_fields),
                "fingerprint_client_assignment_fields": list(v.fingerprint_client_assignment_fields),
            }
            for k, v in sorted(resolved_datasets.items(), key=lambda x: str(x[0]))
        },
        "populations": {str(k): _unstructure(v) for k, v in sorted(populations_dict.items(), key=lambda x: str(x[0]))},
        "experiments": {
            str(k): _experiment_scientific_projection(v)
            for k, v in sorted(experiments_dict.items(), key=lambda x: str(x[0]))
        },
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
        "capabilities": sorted(catalogue_capabilities),
        "suppression_behaviors": sorted(catalogue_suppression_behaviors),
        "population_readiness_rule": dict(sorted(catalogue_population_readiness_rule.items())),
        "eligibility_gates": {k: _unstructure(v) for k, v in sorted(eligibility_gates_dict.items())},
        "analysis_conventions": dict(sorted(catalogue_analysis_conventions.items())),
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
        capabilities=catalogue_capabilities,
        suppression_behaviors=catalogue_suppression_behaviors,
        population_readiness_rule=catalogue_population_readiness_rule,
        eligibility_gates=eligibility_gates_reg,
        analysis_conventions=catalogue_analysis_conventions,
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
