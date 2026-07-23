"""DatpApplication composition root assembling every feature package's use cases and stage
handlers -- the sole module in the codebase permitted to import concrete infrastructure across
package boundaries (section 8.11: nothing is forbidden to ``bootstrap.py``).
"""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.analysis.execution import StatisticalAnalysisStageHandler
from datp_core.analysis.models import StatisticalAnalysisUseCase
from datp_core.artifacts.querying import DuckDbAuditService
from datp_core.artifacts.repository import AtomicArtifactRepository
from datp_core.configuration.loading import ConfigurationError
from datp_core.configuration.project import (
    DescribeResolvedProject,
    ExplainAuthoredConfigurationDrift,
    ExplainExecutionConfigurationDrift,
    ExplainResolvedScientificDrift,
    FingerprintResolvedConfiguration,
    ValidateProjectConfiguration,
    resolve_project_configuration,
)
from datp_core.configuration.resolution import ResolvedProjectConfiguration
from datp_core.datasets.ciciot2023 import CICIoT2023Adapter
from datp_core.datasets.edge_iiotset import EdgeIIoTsetAdapter
from datp_core.datasets.materialization import (
    DatasetAdapterRegistry,
    DatasetMaterializationStageHandler,
    PreflightStageHandler,
)
from datp_core.datasets.models import AdapterKind
from datp_core.datasets.nbaiot import NBaIoTAdapter
from datp_core.datasets.readiness import AuditDatasetUseCase
from datp_core.evaluation.operating_points import OperatingPointEvaluationStageHandler
from datp_core.experiments.execution import ExecuteExperimentUseCase
from datp_core.learning.checkpoints import CohortCheckpointSelectionStageHandler
from datp_core.learning.scoring import ScoreGenerationStageHandler
from datp_core.learning.training import ModelTrainingStageHandler
from datp_core.pipeline.identifiers import ThresholdPolicyId
from datp_core.pipeline.values import TypedDomainRegistry
from datp_core.reporting.execution import ReportGenerationStageHandler, ResultFreezeStageHandler
from datp_core.thresholding.calibration import CalibrationSubsamplingStageHandler
from datp_core.thresholding.construction import (
    ConfiguredThresholdEstimator,
    ConstructThresholdsUseCase,
    ThresholdConstructionStageHandler,
    ThresholdEstimator,
)


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
            AdapterKind.EDGE_IIOTSET: EdgeIIoTsetAdapter(),
        }
    )


@define(frozen=True, slots=True, kw_only=True)
class _CommonConfigUseCases:
    """Configuration-layer use cases shared by both application variants."""

    validate_configuration: ValidateProjectConfiguration
    describe_project: DescribeResolvedProject
    explain_authored_drift: ExplainAuthoredConfigurationDrift
    explain_scientific_drift: ExplainResolvedScientificDrift
    explain_execution_drift: ExplainExecutionConfigurationDrift
    fingerprint_config: FingerprintResolvedConfiguration


def _build_common_config_use_cases(
    resolved_config: ResolvedProjectConfiguration,
) -> _CommonConfigUseCases:
    """Construct configuration-layer use cases shared by both application variants."""
    return _CommonConfigUseCases(
        validate_configuration=ValidateProjectConfiguration(config=resolved_config),
        describe_project=DescribeResolvedProject(config=resolved_config),
        explain_authored_drift=ExplainAuthoredConfigurationDrift(),
        explain_scientific_drift=ExplainResolvedScientificDrift(),
        explain_execution_drift=ExplainExecutionConfigurationDrift(),
        fingerprint_config=FingerprintResolvedConfiguration(),
    )


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
        validate_configuration=cc.validate_configuration,
        describe_project=cc.describe_project,
        explain_authored_drift=cc.explain_authored_drift,
        explain_scientific_drift=cc.explain_scientific_drift,
        explain_execution_drift=cc.explain_execution_drift,
        fingerprint_config=cc.fingerprint_config,
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
    execute_experiment: ExecuteExperimentUseCase
    construct_thresholds: ConstructThresholdsUseCase
    statistical_analysis: StatisticalAnalysisUseCase
    audit_svc: DuckDbAuditService


def build_application(config_dir: Path | None = None) -> DatpApplication:
    """Factory composing the entire DATP application graph without side effects on import."""
    resolved_config = resolve_project_configuration(config_dir=config_dir)

    cc = _build_common_config_use_cases(resolved_config)

    audit_ds = AuditDatasetUseCase()
    artifact_repository = AtomicArtifactRepository(resolved_config.paths.outputs, lock_timeout=30.0)
    adapter_registry = _build_adapter_registry()

    construct_th = ConstructThresholdsUseCase(
        config=resolved_config, registry=_build_estimator_registry(resolved_config)
    )
    statistical_analysis = StatisticalAnalysisUseCase(
        resolved_config.statistical_profiles,
    )
    executor = ExecuteExperimentUseCase(
        config=resolved_config,
        handlers=(
            PreflightStageHandler(resolved_config, artifact_repository),
            DatasetMaterializationStageHandler(resolved_config, artifact_repository, adapter_registry),
            ModelTrainingStageHandler(resolved_config, artifact_repository),
            CohortCheckpointSelectionStageHandler(resolved_config, artifact_repository),
            ScoreGenerationStageHandler(resolved_config, artifact_repository),
            CalibrationSubsamplingStageHandler(resolved_config, artifact_repository),
            ThresholdConstructionStageHandler(resolved_config, artifact_repository, construct_th),
            OperatingPointEvaluationStageHandler(resolved_config, artifact_repository),
            StatisticalAnalysisStageHandler(resolved_config, artifact_repository, statistical_analysis),
            ResultFreezeStageHandler(resolved_config, artifact_repository),
            ReportGenerationStageHandler(resolved_config, artifact_repository),
        ),
    )
    audit_svc = DuckDbAuditService(config=resolved_config)

    return DatpApplication(
        config=resolved_config,
        validate_configuration=cc.validate_configuration,
        describe_project=cc.describe_project,
        explain_authored_drift=cc.explain_authored_drift,
        explain_scientific_drift=cc.explain_scientific_drift,
        explain_execution_drift=cc.explain_execution_drift,
        fingerprint_config=cc.fingerprint_config,
        audit_dataset=audit_ds,
        execute_experiment=executor,
        construct_thresholds=construct_th,
        statistical_analysis=statistical_analysis,
        audit_svc=audit_svc,
    )


__all__ = [
    "ConfigOnlyApplication",
    "ConfigurationError",
    "DatpApplication",
    "build_application",
    "build_config_only_application",
]
