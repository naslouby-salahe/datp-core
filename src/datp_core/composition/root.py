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
from datp_core.application.result_audit import AuditResultsUseCase, QueryResultsUseCase
from datp_core.application.stage_handlers import (
    DatasetMaterializationStageHandler,
    ModelTrainingStageHandler,
    PreflightStageHandler,
    ScoreGenerationStageHandler,
)
from datp_core.application.statistical_analysis import StatisticalAnalysisUseCase
from datp_core.application.threshold_construction import ConstructThresholdsUseCase
from datp_core.config.resolver import ResolvedProjectConfiguration, resolve_project_configuration
from datp_core.domain.datasets import AdapterKind
from datp_core.domain.identifiers import ThresholdPolicyId
from datp_core.domain.values import TypedDomainRegistry
from datp_core.infrastructure.artifacts.atomic_commit import AtomicArtifactRepository
from datp_core.infrastructure.datasets.adapter_registry import DatasetAdapterRegistry
from datp_core.infrastructure.datasets.ciciot2023_adapter import CICIoT2023Adapter
from datp_core.infrastructure.datasets.nbaiot_adapter import NBaIoTAdapter
from datp_core.infrastructure.querying.audit_service import DuckDbAuditService
from datp_core.infrastructure.statistics.scipy_adapter import ScipyStatisticalAnalysisAdapter
from datp_core.infrastructure.thresholding.base import ThresholdEstimator
from datp_core.infrastructure.thresholding.estimators import ConfiguredThresholdEstimator


def _build_estimator_registry(
    config: ResolvedProjectConfiguration,
) -> TypedDomainRegistry[ThresholdPolicyId, ThresholdEstimator]:
    """Bind every estimator to its single resolved policy; no adapter-side policy values exist."""
    estimators: dict[ThresholdPolicyId, ThresholdEstimator] = {
        policy_id: ConfiguredThresholdEstimator(policy_id, policy)
        for policy_id, policy in config.threshold_policies.items()
    }
    return TypedDomainRegistry(_items=estimators)


def _build_adapter_registry() -> DatasetAdapterRegistry:
    """Build the adapter registry with one adapter per supported AdapterKind."""
    return DatasetAdapterRegistry(
        adapters={
            AdapterKind.NBAIOT: NBaIoTAdapter(),
            AdapterKind.CICIOT2023: CICIoT2023Adapter(),
        }
    )


def _build_common_config_use_cases(
    resolved_config: ResolvedProjectConfiguration,
) -> dict[str, object]:
    """Construct configuration-layer use cases shared by both application variants."""
    return {
        "validate_configuration": ValidateProjectConfiguration(config=resolved_config),
        "describe_project": DescribeResolvedProject(config=resolved_config),
        "explain_authored_drift": ExplainAuthoredConfigurationDrift(),
        "explain_scientific_drift": ExplainResolvedScientificDrift(),
        "explain_execution_drift": ExplainExecutionConfigurationDrift(),
        "fingerprint_config": FingerprintResolvedConfiguration(),
    }


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
    cc = _build_common_config_use_cases(resolved_config)
    return ConfigOnlyApplication(
        config=resolved_config,
        validate_configuration=cc["validate_configuration"],  # type: ignore[arg-type]
        describe_project=cc["describe_project"],  # type: ignore[arg-type]
        explain_authored_drift=cc["explain_authored_drift"],  # type: ignore[arg-type]
        explain_scientific_drift=cc["explain_scientific_drift"],  # type: ignore[arg-type]
        explain_execution_drift=cc["explain_execution_drift"],  # type: ignore[arg-type]
        fingerprint_config=cc["fingerprint_config"],  # type: ignore[arg-type]
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
    query_results: QueryResultsUseCase
    audit_results: AuditResultsUseCase


def build_application(config_dir: Path | None = None) -> DatpApplication:
    """Factory composing the entire DATP application graph without side effects on import."""
    resolved_config = resolve_project_configuration(config_dir=config_dir)

    cc = _build_common_config_use_cases(resolved_config)

    audit_ds = AuditDatasetUseCase()
    planner = PlanExperimentUseCase(config=resolved_config)
    artifact_repository = AtomicArtifactRepository(resolved_config.paths.outputs, lock_timeout=30.0)
    adapter_registry = _build_adapter_registry()

    executor = ExecuteExperimentUseCase(
        config=resolved_config,
        handlers=(
            PreflightStageHandler(resolved_config, artifact_repository),
            DatasetMaterializationStageHandler(resolved_config, artifact_repository, adapter_registry),
            ModelTrainingStageHandler(resolved_config, artifact_repository),
            ScoreGenerationStageHandler(resolved_config, artifact_repository),
        ),
    )

    construct_th = ConstructThresholdsUseCase(
        config=resolved_config, registry=_build_estimator_registry(resolved_config)
    )
    statistical_analysis = StatisticalAnalysisUseCase(
        ScipyStatisticalAnalysisAdapter(),
        resolved_config.statistical_profiles,
    )
    audit_svc = DuckDbAuditService(config=resolved_config)
    query_results = QueryResultsUseCase(audit_svc)
    audit_results = AuditResultsUseCase(audit_svc)

    return DatpApplication(
        config=resolved_config,
        validate_configuration=cc["validate_configuration"],  # type: ignore[arg-type]
        describe_project=cc["describe_project"],  # type: ignore[arg-type]
        explain_authored_drift=cc["explain_authored_drift"],  # type: ignore[arg-type]
        explain_scientific_drift=cc["explain_scientific_drift"],  # type: ignore[arg-type]
        explain_execution_drift=cc["explain_execution_drift"],  # type: ignore[arg-type]
        fingerprint_config=cc["fingerprint_config"],  # type: ignore[arg-type]
        audit_dataset=audit_ds,
        plan_experiment=planner,
        execute_experiment=executor,
        construct_thresholds=construct_th,
        statistical_analysis=statistical_analysis,
        query_results=query_results,
        audit_results=audit_results,
    )
