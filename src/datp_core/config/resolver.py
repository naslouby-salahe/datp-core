"""Staged resolution pipeline converting authored YAML documents into an immutable ResolvedProjectConfiguration."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import cast

from attrs import define

from datp_core.config.converter import unstructure_projection
from datp_core.config.dataset_resolution import (
    resolve_datasets,
)
from datp_core.config.experiment_resolution import (
    _experiment_scientific_projection,
    _resolve_analysis,
    _resolve_sweep,
)
from datp_core.config.protocol_resolution import (
    _resolve_artifact_identity,
    _resolve_communication_estimation_contract,
    _resolve_evaluation_result_contract,
    _resolve_metric_definitions,
    _resolve_nested_replicate_policy,
    _resolve_operational_inputs,
    _resolve_protocol_determinism,
    _resolve_report_defaults,
    _resolve_report_profile,
    _resolve_result_type,
    _resolve_threshold_policy,
    _resolve_threshold_policy_defaults,
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
    BatchingRecord,
    CalibrationSubsetRecord,
    CapabilityRequirementRecord,
    CheckpointConvergenceRecord,
    CheckpointProfileRecord,
    CheckpointSelectionRecord,
    EligibilityFallbackRecord,
    EligibilityGateRecord,
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
    PrerequisiteSpecRecord,
    QuantileEstimatorRecord,
    RunRequirement,
    SeedCohortRecord,
    StatisticalProfileRecord,
    TrainingProfileRecord,
)
from datp_core.domain.datasets import (
    ResolvedDataset,
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
    MetricBundleId,
    NormalizationStrategyId,
    PopulationId,
    SeedCohortId,
    StatisticalProfileId,
    ThresholdPolicyId,
    TrainingProfileId,
)
from datp_core.domain.protocol_contracts import (
    ArtifactIdentityRecord,
    CommunicationEstimationContractRecord,
    EvaluationResultContractRecord,
    MetricDefinitionsRecord,
    NestedReplicatePolicyRecord,
    OperationalInputsRecord,
    ProtocolDeterminismRecord,
    ReportDefaultsRecord,
    ReportProfileRecord,
    ResultTypeRecord,
    ThresholdPolicyDefaultsRecord,
)
from datp_core.domain.thresholding import (
    ThresholdPolicyRecord,
)
from datp_core.domain.values import (
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    Probability,
    Seed,
    TypedDomainRegistry,
    deep_freeze,
)


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

    # 1. Resolve datasets (delegated)
    resolved_datasets = resolve_datasets(authored_datasets, paths)

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
                "source_layout_contract": unstructure_projection(v.source_layout_contract),
                "field_schema": unstructure_projection(v.field_schema),
                "source_contract": unstructure_projection(v.source_contract),
                "client_identity_contract": unstructure_projection(v.client_identity_contract),
                "setups": unstructure_projection(v.setups),
                "materializations": unstructure_projection(v.materializations),
                "capabilities": list(v.capabilities),
                "fingerprint_source_fields": list(v.fingerprint_source_fields),
                "fingerprint_schema_fields": list(v.fingerprint_schema_fields),
                "fingerprint_materialization_fields": list(v.fingerprint_materialization_fields),
                "fingerprint_client_assignment_fields": list(v.fingerprint_client_assignment_fields),
            }
            for k, v in sorted(resolved_datasets.items(), key=lambda x: str(x[0]))
        },
        "populations": {
            str(k): unstructure_projection(v) for k, v in sorted(populations_dict.items(), key=lambda x: str(x[0]))
        },
        "experiments": {
            str(k): _experiment_scientific_projection(v)
            for k, v in sorted(experiments_dict.items(), key=lambda x: str(x[0]))
        },
        "threshold_policies": {
            str(k): unstructure_projection(v)
            for k, v in sorted(threshold_policies_dict.items(), key=lambda x: str(x[0]))
        },
        "seed_cohorts": {
            str(k): unstructure_projection(v) for k, v in sorted(seed_dict.items(), key=lambda x: str(x[0]))
        },
        "training_profiles": {
            str(k): unstructure_projection(v) for k, v in sorted(training_dict.items(), key=lambda x: str(x[0]))
        },
        "checkpoint_profiles": {
            str(k): unstructure_projection(v) for k, v in sorted(checkpoint_dict.items(), key=lambda x: str(x[0]))
        },
        "model_architectures": {k: unstructure_projection(v) for k, v in sorted(model_architectures.items())},
        "optimizers": {k: unstructure_projection(v) for k, v in sorted(optimizers.items())},
        "batching": {k: unstructure_projection(v) for k, v in sorted(batching_profiles.items())},
        "eligibility_policies": {
            str(k): unstructure_projection(v) for k, v in sorted(eligibility_policies.items(), key=lambda x: str(x[0]))
        },
        "normalization_strategies": {
            str(k): unstructure_projection(v)
            for k, v in sorted(normalization_strategies.items(), key=lambda x: str(x[0]))
        },
        "quantile_estimators": {k: unstructure_projection(v) for k, v in sorted(quantile_estimators.items())},
        "metric_bundles": {
            str(k): unstructure_projection(v) for k, v in sorted(metric_bundles.items(), key=lambda x: str(x[0]))
        },
        "statistical_profiles": {
            str(k): unstructure_projection(v) for k, v in sorted(statistical_dict.items(), key=lambda x: str(x[0]))
        },
        "metric_definitions": unstructure_projection(resolved_metric_definitions),
        "artifact_identity": unstructure_projection(resolved_artifact_identity),
        "communication_estimation_contract": unstructure_projection(resolved_communication_estimation_contract),
        "operational_inputs": unstructure_projection(resolved_operational_inputs),
        "report_profiles": {k: unstructure_projection(v) for k, v in sorted(report_profiles.items())},
        "communication_estimation": unstructure_projection(resolved_communication_estimation),
        "protocol_determinism": unstructure_projection(resolved_protocol_determinism),
        "normalization_fit_scopes": dict(sorted(resolved_normalization_fit_scopes.items())),
        "normalization_leakage_rule": authored_protocols.normalization_leakage_rule,
        "threshold_policy_defaults": unstructure_projection(resolved_threshold_policy_defaults),
        "nested_replicate_policy": unstructure_projection(resolved_nested_replicate_policy),
        "result_types": {k: unstructure_projection(v) for k, v in sorted(result_types.items())},
        "evaluation_result_contract": unstructure_projection(resolved_evaluation_result_contract),
        "report_defaults": unstructure_projection(resolved_report_defaults),
        "capabilities": sorted(catalogue_capabilities),
        "suppression_behaviors": sorted(catalogue_suppression_behaviors),
        "population_readiness_rule": dict(sorted(catalogue_population_readiness_rule.items())),
        "eligibility_gates": {k: unstructure_projection(v) for k, v in sorted(eligibility_gates_dict.items())},
        "analysis_conventions": dict(sorted(catalogue_analysis_conventions.items())),
    }
    scientific_fingerprint = compute_scientific_fingerprint(scientific_projection)

    execution_projection = {
        "scientific_fingerprint": scientific_fingerprint.value,
        "active_execution_profile": unstructure_projection(resolved_runtime.active_execution_profile),
        "determinism": unstructure_projection(resolved_runtime.determinism_enforcement),
        "device_policy": unstructure_projection(resolved_runtime.device_policy_rules),
        "resource_pressure": unstructure_projection(resolved_runtime.resource_pressure_policy),
        "raw_source_policy": unstructure_projection(resolved_runtime.raw_source_policy),
    }
    execution_fingerprint = compute_execution_fingerprint(execution_projection)
    canonical_scientific_projection = canonicalize_value(scientific_projection)
    canonical_execution_projection = canonicalize_value(execution_projection)

    resolved = ResolvedProjectConfiguration(
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
    # Import here to keep resolution records independent from the validation use case while
    # still rejecting cross-document scientific violations before composition can execute.
    from datp_core.config.validation import ProjectConfigurationValidator

    validation_report = ProjectConfigurationValidator().validate(resolved)
    if not validation_report.is_valid:
        raise ConfigurationError(f"Resolved configuration violates scientific guards: {validation_report.errors}")
    return resolved
