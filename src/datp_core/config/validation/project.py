"""Project configuration validator inspecting resolved project configuration against
cross-document invariants. Delegates to focused per-responsibility validators."""

from __future__ import annotations

from collections.abc import Mapping

from datp_core.config.models import ResolvedProjectConfiguration, ValidationReport
from datp_core.core.identifiers import NormalizationStrategyId
from datp_core.data.contracts import ClientConstructionMethod
from datp_core.experiments import (
    ConditionSweepRecord,
    ExperimentRecord,
    MetricAssociationAnalysisRecord,
    PairedThresholdAnalysisRecord,
    SweepConditionAllocation,
    ValueSweepRecord,
)
from datp_core.learning.contracts.enums import CheckpointAuthorization, PersonalizationStrategy, TrainingProfileKind
from datp_core.thresholding.policies.clustering import ClusterThresholdPolicyRecord
from datp_core.thresholding.policies.grouped import FamilyMeanThresholdPolicyRecord
from datp_core.thresholding.policies.shared import (
    CentralizedPooledThresholdPolicyRecord,
    LocalQuantileThresholdPolicyRecord,
    SharedMeanThresholdPolicyRecord,
    SharedPooledThresholdPolicyRecord,
    SharedWeightedThresholdPolicyRecord,
)
from datp_core.thresholding.policies.shrinkage import (
    CalibrationFallbackThresholdPolicyRecord,
    LocalGlobalShrinkageThresholdPolicyRecord,
)


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
            if not isinstance(policy, (
                SharedMeanThresholdPolicyRecord,
                SharedPooledThresholdPolicyRecord,
                SharedWeightedThresholdPolicyRecord,
                LocalQuantileThresholdPolicyRecord,
                CentralizedPooledThresholdPolicyRecord,
                FamilyMeanThresholdPolicyRecord,
                ClusterThresholdPolicyRecord,
                LocalGlobalShrinkageThresholdPolicyRecord,
                CalibrationFallbackThresholdPolicyRecord,
            )):
                continue
            if not config.quantile_estimators.contains(policy.quantile_estimator):
                errors.append(
                    f"Threshold policy '{tp_id}' references unregistered quantile estimator '{policy.quantile_estimator}'"
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
                        f"'{exp_rec.evidence_role.value}', which result type '{analysis.result_type}' "
                        f"does not permit (allowed: {', '.join(result_type.permitted_evidence_roles)})"
                    )
            if not config.statistical_profiles.contains(analysis.statistical_profile):
                errors.append(
                    f"Experiment '{exp_id}' analysis '{analysis.label}' references "
                    f"unregistered statistical profile '{analysis.statistical_profile}'"
                )
            secondary_profile = None
            if isinstance(analysis, (PairedThresholdAnalysisRecord, MetricAssociationAnalysisRecord)):
                secondary_profile = analysis.secondary_statistical_profile
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
