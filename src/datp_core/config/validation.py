"""Validation rules protecting catalogue consistency and dependency references."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.config.resolver import ResolvedProjectConfiguration, resolve_project_configuration
from datp_core.config.yaml_loader import ConfigurationError
from datp_core.domain.catalogue import ConditionSweepRecord
from datp_core.domain.identifiers import NormalizationStrategyId
from datp_core.domain.thresholding import FamilyMeanThresholdPolicyRecord


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

        # 1. Validate dataset paths, setups, and materialization normalization references
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

        # 2. Validate training profiles reference registered architecture/optimizer/batching
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

        # 3. Validate every configured threshold policy's quantile estimator is registered
        for tp_id, policy in config.threshold_policies.items():
            quantile_estimator = getattr(policy, "quantile_estimator", None)
            if quantile_estimator is not None and not config.quantile_estimators.contains(quantile_estimator):
                errors.append(
                    f"Threshold policy '{tp_id}' references unregistered quantile estimator '{quantile_estimator}'"
                )

        # 4. Validate experiments
        experiment_ids = set(config.experiments)
        if "partition" not in config.protocol_determinism.seed_namespaces:
            errors.append("Protocol determinism lacks the required partition seed namespace")
        for exp_id, exp_rec in config.experiments.items():
            if not config.training_profiles.contains(exp_rec.training_profile_id):
                errors.append(
                    f"Experiment '{exp_id}' references missing training profile '{exp_rec.training_profile_id}'"
                )
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

            partition_conditions = tuple(
                condition
                for sweep in exp_rec.sweeps
                if isinstance(sweep, ConditionSweepRecord)
                for condition in sweep.conditions
            )
            population = config.populations.get(exp_rec.population_ids[0])
            setup = config.datasets.get(population.dataset_id).setup(population.setup_id)
            is_dirichlet_setup = setup.client_construction.method == "dirichlet_partitioned_clients"
            if is_dirichlet_setup != bool(partition_conditions):
                errors.append(
                    f"Experiment '{exp_id}' and dataset setup '{setup.identifier.value}' disagree "
                    "on partition conditions"
                )
            for condition in partition_conditions:
                if condition.allocation == "dirichlet" and (
                    condition.dirichlet_alpha is None or condition.dirichlet_alpha <= 0.0
                ):
                    errors.append(
                        f"Experiment '{exp_id}' condition '{condition.name}' requires a positive Dirichlet alpha"
                    )
                if condition.allocation == "equal_across_source_domains" and condition.dirichlet_alpha is not None:
                    errors.append(
                        f"Experiment '{exp_id}' IID condition '{condition.name}' must not declare a Dirichlet alpha"
                    )
                if condition.allocation not in {"dirichlet", "equal_across_source_domains"}:
                    errors.append(
                        f"Experiment '{exp_id}' condition '{condition.name}' has unsupported allocation "
                        f"'{condition.allocation}'"
                    )

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

            for analysis in exp_rec.analyses:
                if analysis.result_type not in config.result_types:
                    errors.append(
                        f"Experiment '{exp_id}' analysis '{analysis.label}' references "
                        f"unregistered result type '{analysis.result_type}'"
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

        # 5. Validate catalogue-level eligibility gates reference registered experiments
        for gate_id, gate in config.eligibility_gates.items():
            for target_experiment_id in gate.applies_to_experiments:
                if target_experiment_id not in experiment_ids:
                    errors.append(
                        f"Eligibility gate '{gate_id}' references unregistered experiment '{target_experiment_id}'"
                    )

        is_valid = len(errors) == 0
        return ValidationReport(
            is_valid=is_valid,
            errors=tuple(errors),
            warnings=tuple(warnings),
            datasets_checked=len(config.datasets),
            experiments_checked=len(config.experiments),
            threshold_policies_checked=len(config.threshold_policies),
        )


def validate_all_configurations(
    config_dir: Path | None = None,
) -> ValidationReport:
    """Resolve configuration and run validation rules."""
    resolved = resolve_project_configuration(config_dir=config_dir)
    validator = ProjectConfigurationValidator()
    report = validator.validate(resolved)
    if not report.is_valid:
        raise ConfigurationError(f"Configuration validation failed with errors: {report.errors}")
    return report
