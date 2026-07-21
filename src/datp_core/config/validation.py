"""Validation rules protecting catalogue consistency and dependency references."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.config.resolver import ResolvedProjectConfiguration, resolve_project_configuration
from datp_core.config.yaml_loader import ConfigurationError
from datp_core.domain.identifiers import NormalizationStrategyId, StatisticalProfileId


@define(frozen=True, slots=True, kw_only=True)
class ValidationReport:
    """Typed validation result report."""

    is_valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    datasets_checked: int
    experiments_checked: int
    threshold_policies_checked: int

    def __eq__(self, other: object) -> bool:
        if isinstance(other, bool):
            return self.is_valid == other
        return super().__eq__(other)


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
            for prerequisite_id in exp_rec.prerequisite_ids:
                if prerequisite_id not in experiment_ids:
                    errors.append(f"Experiment '{exp_id}' references unregistered prerequisite '{prerequisite_id}'")
            for report_id in exp_rec.report_ids:
                if not config.report_profiles.contains(report_id):
                    errors.append(f"Experiment '{exp_id}' references unregistered report profile '{report_id}'")

            for ev in exp_rec.evaluations:
                if ev.threshold_policy_id not in config.threshold_policies:
                    errors.append(
                        f"Experiment '{exp_id}' evaluation '{ev.label}' references "
                        f"unregistered threshold policy '{ev.threshold_policy_id}'"
                    )

            for analysis in exp_rec.analyses:
                if analysis.result_type not in config.result_types:
                    errors.append(
                        f"Experiment '{exp_id}' analysis '{analysis.label}' references "
                        f"unregistered result type '{analysis.result_type}'"
                    )
                if analysis.statistical_profile is not None and not config.statistical_profiles.contains(
                    StatisticalProfileId(analysis.statistical_profile)
                ):
                    errors.append(
                        f"Experiment '{exp_id}' analysis '{analysis.label}' references "
                        f"unregistered statistical profile '{analysis.statistical_profile}'"
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
