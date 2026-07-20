"""Staged resolution pipeline converting authored YAML documents into an immutable ResolvedProjectConfiguration."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.config.models.dataset_config import CategoricalEncodingConfig
from datp_core.config.models.protocol_config import (
    BatchingProfileConfig,
    EligibilityPolicyConfig,
    MetricBundleConfig,
    ModelArchitectureConfig,
    NormalizationStrategyConfig,
    OptimizerProfileConfig,
    QuantileEstimatorConfig,
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
    CapabilityRequirementRecord,
    CheckpointProfileRecord,
    EvaluationSpecRecord,
    EvidenceRole,
    ExperimentRecord,
    FederationProfileRecord,
    PopulationRecord,
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
from datp_core.domain.values import PositiveInt, Probability, RelativePath, Seed, TypedDomainRegistry


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
    model_architectures: dict[str, ModelArchitectureConfig]
    optimizers: dict[str, OptimizerProfileConfig]
    batching_profiles: dict[str, BatchingProfileConfig]
    eligibility_policies: dict[EligibilityPolicyId, EligibilityPolicyConfig]
    normalization_strategies: dict[NormalizationStrategyId, NormalizationStrategyConfig]
    quantile_estimators: dict[str, QuantileEstimatorConfig]
    metric_bundles: dict[MetricBundleId, MetricBundleConfig]
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
        if "rule" not in cp_cfg.selection:
            raise ConfigurationError(f"Checkpoint profile '{cp_key}' selection has no rule")
        checkpoint_dict[cp_id] = CheckpointProfileRecord(
            identifier=cp_id,
            total_rounds=PositiveInt(total_rounds),
            selected_rounds=tuple(PositiveInt(round_number) for round_number in (selected_rounds or ())),
            early_stopping=cp_cfg.early_stopping,
            selection_rule=str(cp_cfg.selection["rule"]),
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
    for profile_key, raw_profile in authored_protocols.statistical_profiles.items():
        if not isinstance(raw_profile, dict):
            raise ConfigurationError(f"Statistical profile '{profile_key}' must be a mapping")
        method = raw_profile.get("method")
        confidence = raw_profile.get("confidence_level")
        resample_count = raw_profile.get("resample_count")
        minimum_units = raw_profile.get("minimum_paired_units", raw_profile.get("minimum_units"))
        if method is not None and not isinstance(method, str):
            raise ConfigurationError(f"Statistical profile '{profile_key}' has an invalid method")
        if confidence is not None and (not isinstance(confidence, float) or isinstance(confidence, bool)):
            raise ConfigurationError(f"Statistical profile '{profile_key}' has an invalid confidence level")
        if resample_count is not None and (not isinstance(resample_count, int) or isinstance(resample_count, bool)):
            raise ConfigurationError(f"Statistical profile '{profile_key}' has an invalid resample count")
        if minimum_units is not None and (not isinstance(minimum_units, int) or isinstance(minimum_units, bool)):
            raise ConfigurationError(f"Statistical profile '{profile_key}' has an invalid minimum-unit count")
        profile_id = StatisticalProfileId(profile_key)
        statistical_dict[profile_id] = StatisticalProfileRecord(
            identifier=profile_id,
            method=method,
            confidence_level=Probability(confidence) if confidence is not None else None,
            resample_count=PositiveInt(resample_count) if resample_count is not None else None,
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
    model_architectures = authored_protocols.model_architectures
    optimizers = authored_protocols.optimizers
    batching_profiles = authored_protocols.batching
    eligibility_policies = {EligibilityPolicyId(k): v for k, v in authored_protocols.eligibility_policies.items()}
    normalization_strategies = {
        NormalizationStrategyId(k): v for k, v in authored_protocols.normalization_strategies.items()
    }
    quantile_estimators = authored_protocols.quantile_estimators
    metric_bundles = {MetricBundleId(k): v for k, v in authored_protocols.metric_bundles.items()}

    # Scientific fingerprint computation over full scientific content
    scientific_projection = {
        "datasets": {str(k): v.schema_id for k, v in sorted(resolved_datasets.items(), key=lambda x: str(x[0]))},
        "populations": sorted([str(k) for k in populations_dict.keys()]),
        "experiments": sorted([str(k) for k in experiments_dict.keys()]),
        "threshold_policies": sorted([str(k) for k in threshold_policies_dict.keys()]),
        "seed_cohorts": {str(k): v.training_seeds for k, v in sorted(seed_dict.items(), key=lambda x: str(x[0]))},
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
