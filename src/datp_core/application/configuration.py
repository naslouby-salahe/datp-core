"""Application use cases for configuration validation, project description, and drift explanation."""

from __future__ import annotations

from pathlib import Path

from attrs import define
from deepdiff import DeepDiff

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.config.validation import ProjectConfigurationValidator
from datp_core.domain.fingerprints import Fingerprint


@define(frozen=True, slots=True, kw_only=True)
class ConfigurationDriftReport:
    """Report detailing structural or value differences between two configurations."""

    has_drift: bool
    drift_kind: str
    diff_details: dict[str, str]


class ValidateProjectConfiguration:
    """Use case to validate project configuration files against structural and cross-document rules."""

    def __init__(self, config: ResolvedProjectConfiguration) -> None:
        self._config = config

    def execute(self) -> bool:
        report = ProjectConfigurationValidator().validate(self._config)
        return report.is_valid


class DescribeResolvedProject:
    """Use case returning the single resolved project configuration."""

    def __init__(self, config: ResolvedProjectConfiguration) -> None:
        self._config = config

    def execute(self) -> ResolvedProjectConfiguration:
        return self._config


class ExplainAuthoredConfigurationDrift:
    """Use case comparing two authored YAML files and reporting differences."""

    def execute(self, current_yaml_path: Path, expected_yaml_path: Path) -> ConfigurationDriftReport:
        curr_text = current_yaml_path.read_text(encoding="utf-8")
        exp_text = expected_yaml_path.read_text(encoding="utf-8")
        diff = DeepDiff(exp_text, curr_text, ignore_order=True)
        has_drift = len(diff) > 0
        diff_str_map = {str(k): str(v) for k, v in diff.items()}
        return ConfigurationDriftReport(
            has_drift=has_drift,
            drift_kind="authored_yaml",
            diff_details=diff_str_map,
        )


class ExplainResolvedScientificDrift:
    """Use case comparing two resolved project configurations for scientific drift."""

    def execute(
        self,
        current_config: ResolvedProjectConfiguration,
        expected_config: ResolvedProjectConfiguration,
    ) -> ConfigurationDriftReport:
        same_fingerprint = current_config.scientific_fingerprint.value == expected_config.scientific_fingerprint.value
        if same_fingerprint:
            return ConfigurationDriftReport(has_drift=False, drift_kind="scientific", diff_details={})

        diff = DeepDiff(
            expected_config.scientific_fingerprint.value,
            current_config.scientific_fingerprint.value,
            ignore_order=True,
        )
        return ConfigurationDriftReport(
            has_drift=True,
            drift_kind="scientific",
            diff_details={str(k): str(v) for k, v in diff.items()},
        )


class ExplainExecutionConfigurationDrift:
    """Use case comparing execution profiles for runtime execution drift."""

    def execute(
        self,
        current_config: ResolvedProjectConfiguration,
        expected_config: ResolvedProjectConfiguration,
    ) -> ConfigurationDriftReport:
        same_fingerprint = current_config.execution_fingerprint.value == expected_config.execution_fingerprint.value
        if same_fingerprint:
            return ConfigurationDriftReport(has_drift=False, drift_kind="execution", diff_details={})

        diff = DeepDiff(
            expected_config.execution_fingerprint.value,
            current_config.execution_fingerprint.value,
            ignore_order=True,
        )
        return ConfigurationDriftReport(
            has_drift=True,
            drift_kind="execution",
            diff_details={str(k): str(v) for k, v in diff.items()},
        )


class FingerprintResolvedConfiguration:
    """Use case computing scientific and execution fingerprints for a resolved project configuration."""

    def execute(self, config: ResolvedProjectConfiguration) -> tuple[Fingerprint, Fingerprint]:
        return config.scientific_fingerprint, config.execution_fingerprint
