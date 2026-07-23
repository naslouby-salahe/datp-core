"""The sole caller allowed to import both configuration/resolution.py and configuration/validation.py.

Implements the mandated one-directional resolution flow (section 8.1): resolve the candidate,
validate it, and only then return the final immutable ``ResolvedProjectConfiguration``. Also owns
the configuration-facing use cases (drift explanation, fingerprinting, project description) that
previously lived in ``application/configuration.py``, plus the deterministic canonical-projection
diffing that previously lived in ``domain/drift.py``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from attrs import define

from datp_core.configuration.loading import ConfigurationError, RuntimeBootstrapSettings, YamlConfigurationReader
from datp_core.configuration.resolution import ResolvedProjectConfiguration, resolve_project_configuration_candidate
from datp_core.configuration.validation import ProjectConfigurationValidator, ValidationReport
from datp_core.pipeline.fingerprints import CanonicalProjection, Fingerprint, canonicalize_value


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


def resolve_project_configuration(
    config_dir: Path | None = None,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ResolvedProjectConfiguration:
    """Resolve and validate the complete project configuration -- the sole public entry point.

    Matches the pre-refactor ``config/resolver.py::resolve_project_configuration`` behavior exactly
    (resolve, then validate, then return or raise), just with resolution and validation now living
    in separate non-circular modules instead of one module importing the other mid-function.
    """
    candidate = resolve_project_configuration_candidate(config_dir=config_dir, bootstrap_settings=bootstrap_settings)
    validation_report = ProjectConfigurationValidator().validate(candidate)
    if not validation_report.is_valid:
        raise ConfigurationError(f"Resolved configuration violates scientific guards: {validation_report.errors}")
    return candidate


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
