"""The project-configuration composition authority.

Loads authored documents, calls the focused per-document resolvers in ``config/resolve/``,
performs cross-document validation, constructs fingerprints, and produces the immutable
``ResolvedProjectConfiguration`` -- the single resolved project configuration authority loaded
once during composition root initialization. Also owns the configuration-facing use cases (drift
explanation, fingerprinting, project description) and the deterministic canonical-projection
diffing consumed by those use cases.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Literal

from attrs import define

from datp_core.artifacts.models import ArtifactIdentityRecord
from datp_core.config.fingerprints import compute_fingerprint, unstructure_projection
from datp_core.config.loading import (
    ConfigurationError,
    RuntimeBootstrapSettings,
    YamlConfigurationReader,
    resolve_config_root,
)
from datp_core.config.resolve.datasets import resolve_datasets
from datp_core.config.resolve.experiments import ResolvedExperimentCatalogue, resolve_experiment_catalogue
from datp_core.config.resolve.protocols import ProtocolDeterminismRecord, ResolvedProtocols, resolve_protocols
from datp_core.config.resolve.runtime import (
    ResolvedProjectPaths,
    ResolvedRuntimeConfiguration,
    resolve_runtime_configuration,
)
from datp_core.contracts.protocols import (
    CommunicationEstimationContractRecord,
    NestedReplicatePolicyRecord,
    OperationalInputsRecord,
    ReportDefaultsRecord,
    ReportProfileRecord,
    ResultTypeRecord,
    StatisticalProfileRecord,
)
from datp_core.core.hashing import CanonicalProjection, Fingerprint, canonicalize_value
from datp_core.core.identifiers import (
    CheckpointProfileId,
    DatasetId,
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
from datp_core.core.values import TypedDomainRegistry
from datp_core.data.contracts import (
    ClientConstructionMethod,
    EligibilityPolicyRecord,
    NormalizationStrategyRecord,
    ResolvedDataset,
)
from datp_core.evaluation.models import EvaluationResultContractRecord, MetricBundleRecord, MetricDefinitionsRecord
from datp_core.experiments.models import (
    ConditionSweepRecord,
    EligibilityGateRecord,
    EvidenceRole,
    ExperimentRecord,
    PopulationRecord,
    SweepConditionAllocation,
    ValueSweepRecord,
)
from datp_core.learning.models import (
    BatchingRecord,
    CheckpointAuthorization,
    CheckpointProfileRecord,
    ModelArchitectureRecord,
    OptimizerRecord,
    PersonalizationStrategy,
    SeedCohortRecord,
    TrainingProfileKind,
    TrainingProfileRecord,
)
from datp_core.thresholding.models import (
    FamilyMeanThresholdPolicyRecord,
    QuantileEstimatorRecord,
    ThresholdPolicyDefaultsRecord,
    ThresholdPolicyRecord,
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

    def primary_federated_checkpoint_experiment(self) -> ExperimentRecord:
        """Return the sole confirmatory FedAvg experiment authorized to choose the shared round."""
        candidates = tuple(
            experiment
            for experiment in self.experiments.values()
            if experiment.evidence_role is EvidenceRole.CONFIRMATORY
            and self.training_profiles.contains(experiment.training_profile_id)
            and self.training_profiles.get(experiment.training_profile_id).checkpoint_authorization
            == CheckpointAuthorization.PRIMARY_SELECTION_COMPUTED_ONCE
        )
        if len(candidates) != 1:
            raise ValueError("Configuration must define exactly one confirmatory primary FedAvg checkpoint selector")
        return candidates[0]

    def primary_ditto_selection_experiment(self) -> ExperimentRecord:
        """Return the sole natural-regime Ditto experiment allowed to select its proximal weight."""
        candidates = tuple(
            experiment
            for experiment in self.experiments.values()
            if self.training_profiles.contains(experiment.training_profile_id)
            and self.training_profiles.get(experiment.training_profile_id).personalization
            == PersonalizationStrategy.DITTO
            and experiment.personalization_parameter_selection_source is None
        )
        if len(candidates) != 1:
            raise ValueError("Configuration must define exactly one natural-regime Ditto parameter selector")
        return candidates[0]


def _build_scientific_projection(
    *,
    resolved_datasets: dict[DatasetId, ResolvedDataset],
    catalogue: ResolvedExperimentCatalogue,
    protocols: ResolvedProtocols,
) -> dict[str, object]:
    """Assemble the canonical scientific-content projection used for the scientific fingerprint.

    Absolute filesystem paths are deliberately excluded from identity (artifact_identity rule);
    datasets are projected via their schema id, materialization contracts, and fingerprint field
    lists rather than their resolved (absolute-path-bearing) record.
    """
    from datp_core.config.resolve.experiments import _experiment_scientific_projection

    return {
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
            str(k): unstructure_projection(v) for k, v in sorted(catalogue.populations.items(), key=lambda x: str(x[0]))
        },
        "experiments": {
            str(k): _experiment_scientific_projection(v)
            for k, v in sorted(catalogue.experiments.items(), key=lambda x: str(x[0]))
        },
        "threshold_policies": {
            str(k): unstructure_projection(v)
            for k, v in sorted(protocols.threshold_policies.items(), key=lambda x: str(x[0]))
        },
        "seed_cohorts": {
            str(k): unstructure_projection(v)
            for k, v in sorted(protocols.seed_cohorts.items(), key=lambda x: str(x[0]))
        },
        "training_profiles": {
            str(k): unstructure_projection(v)
            for k, v in sorted(protocols.training_profiles.items(), key=lambda x: str(x[0]))
        },
        "checkpoint_profiles": {
            str(k): unstructure_projection(v)
            for k, v in sorted(protocols.checkpoint_profiles.items(), key=lambda x: str(x[0]))
        },
        "model_architectures": {k: unstructure_projection(v) for k, v in sorted(protocols.model_architectures.items())},
        "optimizers": {k: unstructure_projection(v) for k, v in sorted(protocols.optimizers.items())},
        "batching": {k: unstructure_projection(v) for k, v in sorted(protocols.batching_profiles.items())},
        "eligibility_policies": {
            str(k): unstructure_projection(v)
            for k, v in sorted(protocols.eligibility_policies.items(), key=lambda x: str(x[0]))
        },
        "normalization_strategies": {
            str(k): unstructure_projection(v)
            for k, v in sorted(protocols.normalization_strategies.items(), key=lambda x: str(x[0]))
        },
        "quantile_estimators": {k: unstructure_projection(v) for k, v in sorted(protocols.quantile_estimators.items())},
        "metric_bundles": {
            str(k): unstructure_projection(v)
            for k, v in sorted(protocols.metric_bundles.items(), key=lambda x: str(x[0]))
        },
        "statistical_profiles": {
            str(k): unstructure_projection(v)
            for k, v in sorted(protocols.statistical_profiles.items(), key=lambda x: str(x[0]))
        },
        "metric_definitions": unstructure_projection(protocols.metric_definitions),
        "artifact_identity": unstructure_projection(protocols.artifact_identity),
        "communication_estimation_contract": unstructure_projection(protocols.communication_estimation_contract),
        "operational_inputs": unstructure_projection(protocols.operational_inputs),
        "report_profiles": {k: unstructure_projection(v) for k, v in sorted(protocols.report_profiles.items())},
        "communication_estimation": unstructure_projection(protocols.communication_estimation),
        "protocol_determinism": unstructure_projection(protocols.protocol_determinism),
        "normalization_fit_scopes": dict(sorted(protocols.normalization_fit_scopes.items())),
        "normalization_leakage_rule": protocols.normalization_leakage_rule,
        "threshold_policy_defaults": unstructure_projection(protocols.threshold_policy_defaults),
        "nested_replicate_policy": unstructure_projection(protocols.nested_replicate_policy),
        "result_types": {k: unstructure_projection(v) for k, v in sorted(protocols.result_types.items())},
        "evaluation_result_contract": unstructure_projection(protocols.evaluation_result_contract),
        "report_defaults": unstructure_projection(protocols.report_defaults),
        "capabilities": sorted(catalogue.capabilities),
        "suppression_behaviors": sorted(catalogue.suppression_behaviors),
        "population_readiness_rule": dict(sorted(catalogue.population_readiness_rule.items())),
        "eligibility_gates": {k: unstructure_projection(v) for k, v in sorted(catalogue.eligibility_gates.items())},
        "analysis_conventions": dict(sorted(catalogue.analysis_conventions.items())),
    }


def _build_execution_projection(
    *, scientific_fingerprint: Fingerprint, runtime: ResolvedRuntimeConfiguration
) -> dict[str, object]:
    return {
        "scientific_fingerprint": scientific_fingerprint.value,
        "active_execution_profile": unstructure_projection(runtime.active_execution_profile),
        "determinism": unstructure_projection(runtime.determinism_enforcement),
        "device_policy": unstructure_projection(runtime.device_policy_rules),
        "resource_pressure": unstructure_projection(runtime.resource_pressure_policy),
        "raw_source_policy": unstructure_projection(runtime.raw_source_policy),
    }


def resolve_project_configuration_candidate(
    config_dir: Path | None = None,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ResolvedProjectConfiguration:
    """Execute the staged configuration resolution pipeline, returning an UNVALIDATED candidate.

    Callers needing a fully validated configuration must use ``resolve_project_configuration``
    instead, which validates this candidate before returning it. This function must not be called
    directly outside this module and tests that intentionally exercise resolution in isolation
    from validation.
    """
    # execution_profile is required from the environment (DATP_EXECUTION_PROFILE), not a default;
    # see the matching comment in config/resolve/runtime.py.
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
    resolved_datasets = resolve_datasets(authored_datasets, resolved_runtime.paths)
    protocols = resolve_protocols(authored_protocols)
    catalogue = resolve_experiment_catalogue(authored_experiments, resolved_datasets, protocols.threshold_policies)

    scientific_projection = _build_scientific_projection(
        resolved_datasets=resolved_datasets, catalogue=catalogue, protocols=protocols
    )
    scientific_fingerprint = compute_fingerprint("scientific", scientific_projection)
    execution_projection = _build_execution_projection(
        scientific_fingerprint=scientific_fingerprint, runtime=resolved_runtime
    )
    execution_fingerprint = compute_fingerprint("execution", execution_projection)

    return ResolvedProjectConfiguration(
        datasets=TypedDomainRegistry(_items=resolved_datasets),
        populations=catalogue.populations,
        experiments=catalogue.experiments,
        capabilities=catalogue.capabilities,
        suppression_behaviors=catalogue.suppression_behaviors,
        population_readiness_rule=MappingProxyType(catalogue.population_readiness_rule),
        eligibility_gates=catalogue.eligibility_gates,
        analysis_conventions=MappingProxyType(catalogue.analysis_conventions),
        training_profiles=protocols.training_profiles,
        checkpoint_profiles=protocols.checkpoint_profiles,
        seed_cohorts=protocols.seed_cohorts,
        statistical_profiles=protocols.statistical_profiles,
        threshold_policies=TypedDomainRegistry(_items=protocols.threshold_policies),
        model_architectures=protocols.model_architectures,
        optimizers=protocols.optimizers,
        batching_profiles=protocols.batching_profiles,
        eligibility_policies=protocols.eligibility_policies,
        normalization_strategies=protocols.normalization_strategies,
        quantile_estimators=protocols.quantile_estimators,
        metric_bundles=protocols.metric_bundles,
        metric_definitions=protocols.metric_definitions,
        artifact_identity=protocols.artifact_identity,
        communication_estimation_contract=protocols.communication_estimation_contract,
        operational_inputs=protocols.operational_inputs,
        report_profiles=protocols.report_profiles,
        communication_estimation=protocols.communication_estimation,
        protocol_determinism=protocols.protocol_determinism,
        normalization_fit_scopes=MappingProxyType(protocols.normalization_fit_scopes),
        normalization_leakage_rule=protocols.normalization_leakage_rule,
        threshold_policy_defaults=protocols.threshold_policy_defaults,
        nested_replicate_policy=protocols.nested_replicate_policy,
        result_types=protocols.result_types,
        evaluation_result_contract=protocols.evaluation_result_contract,
        report_defaults=protocols.report_defaults,
        runtime=resolved_runtime,
        paths=resolved_runtime.paths,
        scientific_fingerprint=scientific_fingerprint,
        execution_fingerprint=execution_fingerprint,
        scientific_projection=canonicalize_value(scientific_projection),
        execution_projection=canonicalize_value(execution_projection),
    )


@define(frozen=True, slots=True, kw_only=True)
class ValidationReport:
    """Typed validation result report."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    datasets_checked: int
    experiments_checked: int
    threshold_policies_checked: int


class ProjectConfigurationValidator:
    """Validator inspecting resolved project configuration against cross-document invariants."""

    def validate(self, config: ResolvedProjectConfiguration) -> ValidationReport:
        errors: list[str] = []
        warnings: list[str] = []

        self._validate_datasets(config, errors, warnings)
        self._validate_training_profiles(config, errors)
        self._validate_threshold_policy_estimators(config, errors)
        self._validate_experiments(config, errors)
        self._validate_eligibility_gates(config, errors)

        is_valid = len(errors) == 0
        return ValidationReport(
            is_valid=is_valid,
            errors=tuple(errors),
            warnings=tuple(warnings),
            datasets_checked=len(config.datasets),
            experiments_checked=len(config.experiments),
            threshold_policies_checked=len(config.threshold_policies),
        )

    @staticmethod
    def _validate_datasets(config: ResolvedProjectConfiguration, errors: list[str], warnings: list[str]) -> None:
        for d_id, dataset in config.datasets.items():
            if not dataset.paths.raw_root.exists():
                warnings.append(f"Dataset '{d_id}' raw root directory missing")
            if not config.eligibility_policies.contains(dataset.eligibility_policy_id):
                errors.append(
                    f"Dataset '{d_id}' references missing eligibility policy '{dataset.eligibility_policy_id}'"
                )
            for materialization in dataset.materializations:
                if not config.normalization_strategies.contains(
                    NormalizationStrategyId(materialization.normalization_strategy)
                ):
                    errors.append(
                        f"Dataset '{d_id}' materialization '{materialization.identifier}' references "
                        f"unregistered normalization strategy '{materialization.normalization_strategy}'"
                    )

    @staticmethod
    def _validate_training_profiles(config: ResolvedProjectConfiguration, errors: list[str]) -> None:
        for tp_id, training in config.training_profiles.items():
            if not config.model_architectures.contains(training.model_architecture_id):
                errors.append(
                    f"Training profile '{tp_id}' references unregistered model architecture "
                    f"'{training.model_architecture_id}'"
                )
            if not config.optimizers.contains(training.optimizer_id):
                errors.append(f"Training profile '{tp_id}' references unregistered optimizer '{training.optimizer_id}'")
            if not config.batching_profiles.contains(training.batching_profile_id):
                errors.append(
                    f"Training profile '{tp_id}' references unregistered batching profile "
                    f"'{training.batching_profile_id}'"
                )

    @staticmethod
    def _validate_threshold_policy_estimators(config: ResolvedProjectConfiguration, errors: list[str]) -> None:
        for tp_id, policy in config.threshold_policies.items():
            quantile_estimator = getattr(policy, "quantile_estimator", None)
            if quantile_estimator is not None and not config.quantile_estimators.contains(quantile_estimator):
                errors.append(
                    f"Threshold policy '{tp_id}' references unregistered quantile estimator '{quantile_estimator}'"
                )

    @staticmethod
    def _validate_experiment_training_profile(
        exp_id: object, exp_rec: ExperimentRecord, config: ResolvedProjectConfiguration, errors: list[str]
    ) -> None:
        profile = config.training_profiles.get(exp_rec.training_profile_id)
        if profile.personalization == PersonalizationStrategy.DITTO and (
            profile.kind != TrainingProfileKind.FEDERATED_AVERAGING_TRAINING
            or profile.personalized_local_epochs is None
            or profile.personalization_parameter_grid is None
            or not profile.personalization_parameter_grid
            or any(weight <= 0.0 for weight in profile.personalization_parameter_grid)
            or profile.checkpoint_authorization != CheckpointAuthorization.LOOKUP_OF_FEDERATED_AVERAGING
        ):
            errors.append(
                f"Ditto experiment '{exp_id}' requires positive configured personalization epochs and grid "
                "with locked FedAvg checkpoint lookup"
            )
        if profile.kind == TrainingProfileKind.FEDERATED_PROX_TRAINING:
            configured_grid = profile.mu_grid
            override = exp_rec.training_overrides.get("mu") if exp_rec.training_overrides is not None else None
            sweep_name = override.get("from_sweep") if isinstance(override, Mapping) else None
            values = tuple(
                value
                for sweep in exp_rec.sweeps
                if isinstance(sweep, ValueSweepRecord) and sweep.name == sweep_name
                for value in sweep.values
            )
            if (
                configured_grid is None
                or not configured_grid
                or any(value <= 0.0 for value in configured_grid)
                or profile.mu_zero_forbidden_as_a_fedprox_condition is not True
                or values != configured_grid
            ):
                errors.append(
                    f"FedProx experiment '{exp_id}' must bind its exact positive configured mu grid "
                    "through training_overrides"
                )

    @staticmethod
    def _validate_experiment_partition_conditions(
        exp_id: object, exp_rec: ExperimentRecord, config: ResolvedProjectConfiguration, errors: list[str]
    ) -> None:
        partition_conditions = tuple(
            condition
            for sweep in exp_rec.sweeps
            if isinstance(sweep, ConditionSweepRecord)
            for condition in sweep.conditions
        )
        population = config.populations.get(exp_rec.population_ids[0])
        setup = config.datasets.get(population.dataset_id).setup(population.setup_id)
        is_dirichlet_setup = setup.client_construction.method == ClientConstructionMethod.DIRICHLET_PARTITIONED_CLIENTS
        if is_dirichlet_setup != bool(partition_conditions):
            errors.append(
                f"Experiment '{exp_id}' and dataset setup '{setup.identifier.value}' disagree on partition conditions"
            )
        for condition in partition_conditions:
            if condition.allocation == SweepConditionAllocation.DIRICHLET and (
                condition.dirichlet_alpha is None or condition.dirichlet_alpha <= 0.0
            ):
                errors.append(f"Experiment '{exp_id}' condition '{condition.name}' requires a positive Dirichlet alpha")
            if (
                condition.allocation == SweepConditionAllocation.EQUAL_ACROSS_SOURCE_DOMAINS
                and condition.dirichlet_alpha is not None
            ):
                errors.append(
                    f"Experiment '{exp_id}' IID condition '{condition.name}' must not declare a Dirichlet alpha"
                )
            if condition.allocation not in {
                SweepConditionAllocation.DIRICHLET,
                SweepConditionAllocation.EQUAL_ACROSS_SOURCE_DOMAINS,
            }:
                errors.append(
                    f"Experiment '{exp_id}' condition '{condition.name}' has unsupported allocation "
                    f"'{condition.allocation}'"
                )

    @staticmethod
    def _validate_experiment_evaluations(
        exp_id: object, exp_rec: ExperimentRecord, config: ResolvedProjectConfiguration, errors: list[str]
    ) -> None:
        for ev in exp_rec.evaluations:
            if ev.threshold_policy_id not in config.threshold_policies:
                errors.append(
                    f"Experiment '{exp_id}' evaluation '{ev.label}' references "
                    f"unregistered threshold policy '{ev.threshold_policy_id}'"
                )
                continue
            policy = config.threshold_policies[ev.threshold_policy_id]
            target_population = config.populations.get(ev.population_id or exp_rec.population_ids[0])
            target_dataset = config.datasets.get(target_population.dataset_id)
            if (
                isinstance(policy, FamilyMeanThresholdPolicyRecord)
                and "family_taxonomy" not in target_dataset.capabilities
            ):
                errors.append(
                    f"Experiment '{exp_id}' evaluation '{ev.label}' requests B3 on a population without "
                    "a family taxonomy"
                )

    @staticmethod
    def _validate_experiment_analyses(
        exp_id: object, exp_rec: ExperimentRecord, config: ResolvedProjectConfiguration, errors: list[str]
    ) -> None:
        for analysis in exp_rec.analyses:
            if analysis.result_type not in config.result_types:
                errors.append(
                    f"Experiment '{exp_id}' analysis '{analysis.label}' references "
                    f"unregistered result type '{analysis.result_type}'"
                )
            else:
                result_type = config.result_types[analysis.result_type]
                if exp_rec.evidence_role.value not in result_type.permitted_evidence_roles:
                    errors.append(
                        f"Experiment '{exp_id}' analysis '{analysis.label}' has evidence role "
                        f"'{exp_rec.evidence_role.value}', which result type '{analysis.result_type}' does not "
                        f"permit (allowed: {', '.join(result_type.permitted_evidence_roles)})"
                    )
            if not config.statistical_profiles.contains(analysis.statistical_profile):
                errors.append(
                    f"Experiment '{exp_id}' analysis '{analysis.label}' references "
                    f"unregistered statistical profile '{analysis.statistical_profile}'"
                )
            secondary_profile = getattr(analysis, "secondary_statistical_profile", None)
            if secondary_profile is not None and not config.statistical_profiles.contains(secondary_profile):
                errors.append(
                    f"Experiment '{exp_id}' analysis '{analysis.label}' references "
                    f"unregistered secondary statistical profile '{secondary_profile}'"
                )

    def _validate_experiments(self, config: ResolvedProjectConfiguration, errors: list[str]) -> None:
        experiment_ids = set(config.experiments)
        try:
            config.primary_federated_checkpoint_experiment()
        except ValueError as exc:
            errors.append(str(exc))
        try:
            config.primary_ditto_selection_experiment()
        except ValueError as exc:
            errors.append(str(exc))
        if "partition" not in config.protocol_determinism.seed_namespaces:
            errors.append("Protocol determinism lacks the required partition seed namespace")
        for exp_id, exp_rec in config.experiments.items():
            if not config.training_profiles.contains(exp_rec.training_profile_id):
                errors.append(
                    f"Experiment '{exp_id}' references missing training profile '{exp_rec.training_profile_id}'"
                )
                continue
            if not config.checkpoint_profiles.contains(exp_rec.checkpoint_profile_id):
                errors.append(
                    f"Experiment '{exp_id}' references missing checkpoint profile '{exp_rec.checkpoint_profile_id}'"
                )
            if not config.seed_cohorts.contains(exp_rec.seed_cohort_id):
                errors.append(f"Experiment '{exp_id}' references missing seed cohort '{exp_rec.seed_cohort_id}'")
            if not config.eligibility_policies.contains(exp_rec.eligibility_policy_id):
                errors.append(
                    f"Experiment '{exp_id}' references missing eligibility policy '{exp_rec.eligibility_policy_id}'"
                )
            for prerequisite in exp_rec.prerequisites:
                if prerequisite.experiment_id not in experiment_ids:
                    errors.append(
                        f"Experiment '{exp_id}' references unregistered prerequisite '{prerequisite.experiment_id}'"
                    )
            independent_of = exp_rec.independent_of_experiment
            if independent_of is not None and independent_of not in experiment_ids:
                errors.append(
                    f"Experiment '{exp_id}' references unregistered independent_of_experiment "
                    f"'{exp_rec.independent_of_experiment}'"
                )
            for report_id in exp_rec.report_ids:
                if not config.report_profiles.contains(report_id):
                    errors.append(f"Experiment '{exp_id}' references unregistered report profile '{report_id}'")

            self._validate_experiment_training_profile(exp_id, exp_rec, config, errors)
            self._validate_experiment_partition_conditions(exp_id, exp_rec, config, errors)
            self._validate_experiment_evaluations(exp_id, exp_rec, config, errors)
            self._validate_experiment_analyses(exp_id, exp_rec, config, errors)

    @staticmethod
    def _validate_eligibility_gates(config: ResolvedProjectConfiguration, errors: list[str]) -> None:
        for gate_id, gate in config.eligibility_gates.items():
            for target_experiment_id in gate.applies_to_experiments:
                if target_experiment_id not in set(config.experiments):
                    errors.append(
                        f"Eligibility gate '{gate_id}' references unregistered experiment '{target_experiment_id}'"
                    )


def resolve_project_configuration(
    config_dir: Path | None = None,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ResolvedProjectConfiguration:
    """Resolve and validate the complete project configuration -- the sole public entry point."""
    candidate = resolve_project_configuration_candidate(config_dir=config_dir, bootstrap_settings=bootstrap_settings)
    validation_report = ProjectConfigurationValidator().validate(candidate)
    if not validation_report.is_valid:
        raise ConfigurationError(f"Resolved configuration violates scientific guards: {validation_report.errors}")
    return candidate


@define(frozen=True, slots=True, kw_only=True)
class DriftEntry:
    """One structural difference between two canonical projections."""

    path: str
    kind: Literal["changed", "added", "removed"]
    old_value: CanonicalProjection = None
    new_value: CanonicalProjection = None


def diff_canonical_projections(
    before: CanonicalProjection, after: CanonicalProjection, *, path: str = "$"
) -> tuple[DriftEntry, ...]:
    """Walk two canonical projections and report every changed, added, or removed path."""
    entries: list[DriftEntry] = []
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child_path = f"{path}.{key}"
            if key not in before:
                entries.append(DriftEntry(path=child_path, kind="added", new_value=after[key]))
            elif key not in after:
                entries.append(DriftEntry(path=child_path, kind="removed", old_value=before[key]))
            else:
                entries.extend(diff_canonical_projections(before[key], after[key], path=child_path))
    elif isinstance(before, list) and isinstance(after, list):
        for index in range(max(len(before), len(after))):
            child_path = f"{path}[{index}]"
            if index >= len(before):
                entries.append(DriftEntry(path=child_path, kind="added", new_value=after[index]))
            elif index >= len(after):
                entries.append(DriftEntry(path=child_path, kind="removed", old_value=before[index]))
            else:
                entries.extend(diff_canonical_projections(before[index], after[index], path=child_path))
    elif before != after:
        entries.append(DriftEntry(path=path, kind="changed", old_value=before, new_value=after))
    return tuple(entries)


@define(frozen=True, slots=True, kw_only=True)
class ConfigurationDriftReport:
    """Report detailing structural or value differences between two configurations."""

    has_drift: bool
    drift_kind: str
    diff_entries: tuple[DriftEntry, ...]


class ValidateProjectConfiguration:
    """Use case to validate project configuration files against structural and cross-document rules."""

    def __init__(self, config: ResolvedProjectConfiguration) -> None:
        self._config = config

    def execute(self) -> ValidationReport:
        return ProjectConfigurationValidator().validate(self._config)


class DescribeResolvedProject:
    """Use case returning the single resolved project configuration."""

    def __init__(self, config: ResolvedProjectConfiguration) -> None:
        self._config = config

    def execute(self) -> ResolvedProjectConfiguration:
        return self._config


class ExplainAuthoredConfigurationDrift:
    """Use case comparing two authored YAML files and reporting parsed-value differences.

    Both documents are parsed (duplicate-key-safe) before comparison, so formatting, comments,
    whitespace, and key ordering never produce drift -- only an actual authored-value change does.
    """

    def execute(self, current_yaml_path: Path, expected_yaml_path: Path) -> ConfigurationDriftReport:
        current_document = canonicalize_value(YamlConfigurationReader.read_document(current_yaml_path))
        expected_document = canonicalize_value(YamlConfigurationReader.read_document(expected_yaml_path))
        entries = diff_canonical_projections(expected_document, current_document)
        return ConfigurationDriftReport(
            has_drift=len(entries) > 0,
            drift_kind="authored_yaml",
            diff_entries=entries,
        )


class ExplainResolvedScientificDrift:
    """Use case comparing two resolved project configurations for scientific drift."""

    def execute(
        self,
        current_config: ResolvedProjectConfiguration,
        expected_config: ResolvedProjectConfiguration,
    ) -> ConfigurationDriftReport:
        entries = diff_canonical_projections(
            expected_config.scientific_projection, current_config.scientific_projection
        )
        return ConfigurationDriftReport(
            has_drift=len(entries) > 0,
            drift_kind="scientific",
            diff_entries=entries,
        )


class ExplainExecutionConfigurationDrift:
    """Use case comparing execution profiles for runtime execution drift."""

    def execute(
        self,
        current_config: ResolvedProjectConfiguration,
        expected_config: ResolvedProjectConfiguration,
    ) -> ConfigurationDriftReport:
        entries = diff_canonical_projections(expected_config.execution_projection, current_config.execution_projection)
        return ConfigurationDriftReport(
            has_drift=len(entries) > 0,
            drift_kind="execution",
            diff_entries=entries,
        )


class FingerprintResolvedConfiguration:
    """Use case computing scientific and execution fingerprints for a resolved project configuration."""

    def execute(self, config: ResolvedProjectConfiguration) -> tuple[Fingerprint, Fingerprint]:
        return config.scientific_fingerprint, config.execution_fingerprint
