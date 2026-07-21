"""Application use cases for configuration validation, project description, and drift explanation."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.config.resolver import ResolvedProjectConfiguration
from datp_core.config.validation import ProjectConfigurationValidator, ValidationReport
from datp_core.config.yaml_loader import YamlConfigurationReader
from datp_core.domain.drift import DriftEntry, diff_canonical_projections
from datp_core.domain.fingerprints import Fingerprint, canonicalize_value


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
