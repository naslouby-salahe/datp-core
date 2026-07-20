"""Staged resolution pipeline converting authored YAML documents into an immutable ResolvedProjectConfiguration."""

from __future__ import annotations

from pathlib import Path

import cattrs
from attrs import define

from datp_core.config.models.dataset_config import CategoricalEncodingConfig
from datp_core.config.models.protocol_config import (
    TypedThresholdPolicyConfig,
)
from datp_core.config.runtime_settings import (
    ResolvedProjectPaths,
    ResolvedRuntimeConfiguration,
    RuntimeBootstrapSettings,
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
    SweepRecord,
    TrainingProfileRecord,
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
    Fingerprint,
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
from datp_core.domain.values import (
    NonNegativeFloat,
    PositiveFloat,
    PositiveInt,
    Probability,
    RelativePath,
    Seed,
    TypedDomainRegistry,
)


_projection_converter = cattrs.Converter()


def _unstructure(value: object) -> object:
    """Convert resolved attrs records into primitive structures for canonical fingerprinting."""
    return _projection_converter.unstructure(value)


@define(frozen=True, slots=True, kw_only=True)
class ResolvedProjectConfiguration:
    """Single resolved project configuration authority loaded once during composition root initialization."""

    datasets: dict[DatasetId, ResolvedDataset]
    populations: TypedDomainRegistry[PopulationId, PopulationRecord]
    experiments: TypedDomainRegistry[ExperimentId, ExperimentRecord]
    training_profiles: TypedDomainRegistry[TrainingProfileId, TrainingProfileRecord]
    checkpoint_profiles: TypedDomainRegistry[CheckpointProfileId, CheckpointProfileRecord]
    seed_cohorts: TypedDomainRegistry[SeedCohortId, SeedCohortRecord]
    statistical_profiles: TypedDomainRegistry[StatisticalProfileId, StatisticalProfileRecord]
    threshold_policies: dict[ThresholdPolicyId, TypedThresholdPolicyConfig]
    model_architectures: dict[str, ModelArchitectureRecord]
    optimizers: dict[str, OptimizerRecord]
    batching_profiles: dict[str, BatchingRecord]
    eligibility_policies: dict[EligibilityPolicyId, EligibilityPolicyRecord]
    normalization_strategies: dict[NormalizationStrategyId, NormalizationStrategyRecord]
    quantile_estimators: dict[str, QuantileEstimatorRecord]
    metric_bundles: dict[MetricBundleId, MetricBundleRecord]
    runtime: ResolvedRuntimeConfiguration
    paths: ResolvedProjectPaths
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint


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
    if config_dir is None:
        config_dir = (bootstrap_settings or RuntimeBootstrapSettings()).config_root
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
        label_header = multiclass_label.get("column") if multiclass_label is not None else None
        if label_header is not None and not isinstance(label_header, str):
            raise ConfigurationError(f"Dataset '{d_cfg.dataset}' has a non-string multiclass label column")
        if configured_sources is None:
            source_trees = (
                ConfiguredSourceTree(
                    identifier="primary",
                    root=RelativePath(d_cfg.source_layout.root),
                    file_pattern=d_cfg.source_layout.attack_file_pattern or "*.csv",
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
    threshold_policies_dict: dict[ThresholdPolicyId, TypedThresholdPolicyConfig] = {}
    for tp_key, tp_cfg in authored_protocols.threshold_policies.items():
        tp_id = ThresholdPolicyId(tp_key)
        threshold_policies_dict[tp_id] = tp_cfg

    # 7. Resolve experiments
    experiments_dict: dict[ExperimentId, ExperimentRecord] = {}
    for exp_cfg in authored_experiments.experiments:
        exp_id = ExperimentId(exp_cfg.name)

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
            sweeps=tuple(
                SweepRecord(
                    name=name,
                    values=tuple(value for value in sweep.values or () if isinstance(value, str | int | float)),
                )
                for name, sweep in sorted((exp_cfg.sweeps or {}).items())
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
            str(k): v.model_dump(mode="json")
            for k, v in sorted(threshold_policies_dict.items(), key=lambda x: str(x[0]))
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
    }
    scientific_fingerprint = compute_scientific_fingerprint(scientific_projection)

    execution_projection = {
        "scientific_fingerprint": scientific_fingerprint.value,
        "runtime_profiles": sorted(list(resolved_runtime.execution_profiles.keys())),
        "determinism": resolved_runtime.determinism_enforcement,
    }
    execution_fingerprint = compute_execution_fingerprint(execution_projection)

    return ResolvedProjectConfiguration(
        datasets=resolved_datasets,
        populations=populations_reg,
        experiments=experiments_reg,
        training_profiles=training_reg,
        checkpoint_profiles=checkpoint_reg,
        seed_cohorts=seed_reg,
        statistical_profiles=statistical_reg,
        threshold_policies=threshold_policies_dict,
        model_architectures=model_architectures,
        optimizers=optimizers,
        batching_profiles=batching_profiles,
        eligibility_policies=eligibility_policies,
        normalization_strategies=normalization_strategies,
        quantile_estimators=quantile_estimators,
        metric_bundles=metric_bundles,
        runtime=resolved_runtime,
        paths=paths,
        scientific_fingerprint=scientific_fingerprint,
        execution_fingerprint=execution_fingerprint,
    )
