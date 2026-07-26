"""The project-configuration composition authority.

Loads authored documents, calls the focused per-document resolvers in ``config/resolution/``,
performs cross-document validation, constructs fingerprints, and produces the immutable
``ResolvedProjectConfiguration``.
"""

from __future__ import annotations

from pathlib import Path
from types import MappingProxyType

from datp_core.config.bootstrap import RuntimeBootstrapSettings, resolve_config_root
from datp_core.config.errors import ConfigurationError
from datp_core.config.fingerprinting.canonical import compute_fingerprint
from datp_core.config.fingerprinting.drift import (
    ConfigurationDriftReport,
    diff_canonical_projections,
)
from datp_core.config.fingerprinting.execution import build_execution_projection
from datp_core.config.fingerprinting.projection import unstructure_projection
from datp_core.config.fingerprinting.scientific import build_scientific_projection
from datp_core.config.loading import YamlConfigurationReader
from datp_core.config.models import ResolvedProjectConfiguration, ValidationReport
from datp_core.config.resolution.datasets import resolve_datasets
from datp_core.config.resolution.experiments import resolve_experiment_catalogue
from datp_core.config.resolution.protocols import resolve_protocols
from datp_core.config.resolution.runtime import resolve_runtime_configuration
from datp_core.config.validation.project import ProjectConfigurationValidator
from datp_core.core.hashing import Fingerprint, canonicalize_value
from datp_core.core.registry import TypedDomainRegistry


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

    scientific_projection = build_scientific_projection(
        resolved_datasets=resolved_datasets,
        catalogue=catalogue,
        protocols=protocols,
        projection_module=unstructure_projection,
    )
    scientific_fingerprint = compute_fingerprint("scientific", scientific_projection)
    execution_projection = build_execution_projection(
        scientific_fingerprint=scientific_fingerprint,
        runtime=resolved_runtime,
        projection_module=unstructure_projection,
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
