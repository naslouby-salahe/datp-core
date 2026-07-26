"""DatpApplication composition root assembling every feature package's use cases and stage
handlers -- the sole module in the codebase permitted to import concrete infrastructure across
package boundaries.
"""

from __future__ import annotations

from pathlib import Path

from attrs import define

from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.artifacts.store import ArtifactStore
from datp_core.pipeline.stages.analysis import StatisticalAnalysisStageHandler
from datp_core.config.loading import ConfigurationError
from datp_core.config.project import (
    DescribeResolvedProject,
    ExplainAuthoredConfigurationDrift,
    ExplainExecutionConfigurationDrift,
    ExplainResolvedScientificDrift,
    FingerprintResolvedConfiguration,
    ResolvedProjectConfiguration,
    ValidateProjectConfiguration,
    resolve_project_configuration,
)
from datp_core.core.identifiers import ThresholdPolicyId
from datp_core.core.registry import TypedDomainRegistry
from datp_core.data.adapters.ciciot2023 import CICIoT2023Adapter
from datp_core.data.adapters.edge_iiotset import EdgeIIoTsetAdapter
from datp_core.data.adapters.nbaiot import NBaIoTAdapter
from datp_core.data.contracts import AdapterKind
from datp_core.data.materialization import (
    DatasetAdapterRegistry,
    DatasetMaterializationStageHandler,
)
from datp_core.data.readiness import AuditDatasetUseCase
from datp_core.evaluation.execution import OperatingPointEvaluationStageHandler
from datp_core.experiments.execution import (
    CampaignOrchestrator,
    ExecuteExperimentUseCase,
    ExperimentLifecycleUseCase,
    ExperimentOutputManager,
    PreflightStageHandler,
)
from datp_core.learning.checkpoints.handler import CohortCheckpointSelectionStageHandler
from datp_core.learning.scoring.handler import ScoreGenerationStageHandler
from datp_core.learning.training.handler import ModelTrainingStageHandler
from datp_core.reporting.audit.query import DuckDbAuditService
from datp_core.reporting.execution.freeze_handler import ResultFreezeStageHandler
from datp_core.reporting.execution.report_handler import ReportGenerationStageHandler
from datp_core.thresholding.calibration.handler import CalibrationSubsamplingStageHandler
from datp_core.thresholding.estimation.construction import ConstructThresholdsUseCase
from datp_core.thresholding.estimation.dispatch import ConfiguredThresholdEstimator
from datp_core.thresholding.estimation.ports import ThresholdEstimator
from datp_core.thresholding.execution.handler import ThresholdConstructionStageHandler


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
    run_experiment: ExperimentLifecycleUseCase
    run_campaign: CampaignOrchestrator
    output_manager: ExperimentOutputManager
    construct_thresholds: ConstructThresholdsUseCase
    statistical_analysis: StatisticalAnalysisUseCase
    audit_svc: DuckDbAuditService


def build_application(config_dir: Path | None = None) -> DatpApplication:
    """Factory composing the entire DATP application graph without side effects on import."""
    resolved_config = resolve_project_configuration(config_dir=config_dir)

    cc = _build_common_config_use_cases(resolved_config)

    audit_ds = AuditDatasetUseCase()
    output_store = ArtifactStore(resolved_config.paths.outputs)
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
            PreflightStageHandler(resolved_config, output_store),
            DatasetMaterializationStageHandler(resolved_config, output_store, adapter_registry),
            ModelTrainingStageHandler(resolved_config, output_store),
            CohortCheckpointSelectionStageHandler(resolved_config, output_store),
            ScoreGenerationStageHandler(resolved_config, output_store),
            CalibrationSubsamplingStageHandler(resolved_config, output_store),
            ThresholdConstructionStageHandler(resolved_config, output_store, construct_th),
            OperatingPointEvaluationStageHandler(resolved_config, output_store),
            StatisticalAnalysisStageHandler(resolved_config, output_store, statistical_analysis),
            ResultFreezeStageHandler(resolved_config, output_store),
            ReportGenerationStageHandler(resolved_config, output_store),
        ),
    )
    output_manager = ExperimentOutputManager(resolved_config.paths.outputs)
    lifecycle = ExperimentLifecycleUseCase(
        config=resolved_config,
        execute_experiment=executor,
        output_manager=output_manager,
    )
    campaign = CampaignOrchestrator(
        config=resolved_config,
        lifecycle=lifecycle,
        output_manager=output_manager,
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
        run_experiment=lifecycle,
        run_campaign=campaign,
        output_manager=output_manager,
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
