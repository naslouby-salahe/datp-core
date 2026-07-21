"""DatpApplication composition root assembling application use cases and infrastructure ports."""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.application.configuration import (
    DescribeResolvedProject,
    ExplainAuthoredConfigurationDrift,
    ExplainExecutionConfigurationDrift,
    ExplainResolvedScientificDrift,
    FingerprintResolvedConfiguration,
    ValidateProjectConfiguration,
)
from datp_core.application.dataset_audit import AuditDatasetUseCase
from datp_core.application.experiment_execution import ExecuteExperimentUseCase
from datp_core.application.experiment_planning import PlanExperimentUseCase
from datp_core.application.stage_handlers import DatasetMaterializationStageHandler, PreflightStageHandler
from datp_core.application.statistical_analysis import StatisticalAnalysisUseCase
from datp_core.application.threshold_construction import ConstructThresholdsUseCase, build_estimator_registry
from datp_core.config.resolver import ResolvedProjectConfiguration, resolve_project_configuration
from datp_core.infrastructure.artifacts.atomic_commit import AtomicArtifactRepository
from datp_core.infrastructure.querying.audit_service import DuckDbAuditService
from datp_core.infrastructure.statistics.scipy_port import ScipyStatisticalAnalysisAdapter


@define(frozen=True, slots=True, kw_only=True)
class ConfigOnlyApplication:
    """Lightweight composition root for configuration-only operations.

    Built from just YAML load + validate + resolve -- no artifact repository, no DuckDB
    service, no threshold estimators, no statistics adapter, no execution use case. Used by CLI
    commands that only read or explain configuration, so they never pay for the full
    application graph.
    """

    config: ResolvedProjectConfiguration
    validate_configuration: ValidateProjectConfiguration
    describe_project: DescribeResolvedProject
    explain_authored_drift: ExplainAuthoredConfigurationDrift
    explain_scientific_drift: ExplainResolvedScientificDrift
    explain_execution_drift: ExplainExecutionConfigurationDrift
    fingerprint_config: FingerprintResolvedConfiguration


def build_config_only_application(config_dir: Path | None = None) -> ConfigOnlyApplication:
    """Factory composing only the configuration-layer use cases, with no infrastructure."""
    resolved_config = resolve_project_configuration(config_dir=config_dir)
    return ConfigOnlyApplication(
        config=resolved_config,
        validate_configuration=ValidateProjectConfiguration(config=resolved_config),
        describe_project=DescribeResolvedProject(config=resolved_config),
        explain_authored_drift=ExplainAuthoredConfigurationDrift(),
        explain_scientific_drift=ExplainResolvedScientificDrift(),
        explain_execution_drift=ExplainExecutionConfigurationDrift(),
        fingerprint_config=FingerprintResolvedConfiguration(),
    )


@define(frozen=True, slots=True, kw_only=True)
class DatpApplication:
    """Composition root holding resolved configuration and injected use cases."""

    config: ResolvedProjectConfiguration
    validate_configuration: ValidateProjectConfiguration
    describe_project: DescribeResolvedProject
    explain_authored_drift: ExplainAuthoredConfigurationDrift
    explain_scientific_drift: ExplainResolvedScientificDrift
    explain_execution_drift: ExplainExecutionConfigurationDrift
    fingerprint_config: FingerprintResolvedConfiguration
    audit_dataset: AuditDatasetUseCase
    plan_experiment: PlanExperimentUseCase
    execute_experiment: ExecuteExperimentUseCase
    construct_thresholds: ConstructThresholdsUseCase
    statistical_analysis: StatisticalAnalysisUseCase
    audit_service: DuckDbAuditService


def build_application(config_dir: Path | None = None) -> DatpApplication:
    """Factory composing the entire DATP application graph without side effects on import."""
    resolved_config = resolve_project_configuration(config_dir=config_dir)

    validate_cfg = ValidateProjectConfiguration(config=resolved_config)
    describe_proj = DescribeResolvedProject(config=resolved_config)
    explain_authored = ExplainAuthoredConfigurationDrift()
    explain_scientific = ExplainResolvedScientificDrift()
    explain_execution = ExplainExecutionConfigurationDrift()
    fingerprint_usecase = FingerprintResolvedConfiguration()

    audit_ds = AuditDatasetUseCase()
    planner = PlanExperimentUseCase(config=resolved_config)
    artifact_repository = AtomicArtifactRepository(resolved_config.paths.outputs, lock_timeout=30.0)
    executor = ExecuteExperimentUseCase(
        config=resolved_config,
        handlers=(
            PreflightStageHandler(resolved_config, artifact_repository),
            DatasetMaterializationStageHandler(resolved_config, artifact_repository),
        ),
    )
    construct_th = ConstructThresholdsUseCase(
        config=resolved_config, registry=build_estimator_registry(resolved_config)
    )
    statistical_analysis = StatisticalAnalysisUseCase(
        ScipyStatisticalAnalysisAdapter(),
        resolved_config.statistical_profiles,
    )
    audit_svc = DuckDbAuditService(config=resolved_config)

    return DatpApplication(
        config=resolved_config,
        validate_configuration=validate_cfg,
        describe_project=describe_proj,
        explain_authored_drift=explain_authored,
        explain_scientific_drift=explain_scientific,
        explain_execution_drift=explain_execution,
        fingerprint_config=fingerprint_usecase,
        audit_dataset=audit_ds,
        plan_experiment=planner,
        execute_experiment=executor,
        construct_thresholds=construct_th,
        statistical_analysis=statistical_analysis,
        audit_service=audit_svc,
    )
