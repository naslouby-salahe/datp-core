"""Validation rules protecting catalogue consistency and dependency references."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.config.resolver import ResolvedProjectConfiguration, resolve_project_configuration
from datp_core.config.yaml_loader import ConfigurationError


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

        # 1. Validate dataset paths and setups
        for d_id, dataset in config.datasets.items():
            if not dataset.paths.raw_root.exists():
                warnings.append(f"Dataset '{d_id}' raw root directory missing")

        # 2. Validate experiments
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

            for ev in exp_rec.evaluations:
                if ev.threshold_policy_id not in config.threshold_policies:
                    errors.append(
                        f"Experiment '{exp_id}' evaluation '{ev.label}' references "
                        f"unregistered threshold policy '{ev.threshold_policy_id}'"
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
