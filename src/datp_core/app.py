"""DatpApplication composition root assembling every feature package's use cases and stage
handlers -- the sole module in the codebase permitted to import concrete infrastructure across
package boundaries.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.artifacts.store import ArtifactStore
from datp_core.config.bootstrap import RuntimeBootstrapSettings
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
from datp_core.core.identifiers import ExperimentId, ThresholdPolicyId
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
    CampaignRunner,
    ExecuteExperimentUseCase,
    ExperimentOutputManager,
    ExperimentRunner,
    PreflightStageHandler,
)
from datp_core.experiments.planning.builder import ExperimentPlanBuilder
from datp_core.experiments.planning.paths import ExperimentPaths
from datp_core.learning.checkpoints.handler import CohortCheckpointSelectionStageHandler
from datp_core.learning.scoring.handler import (
    ScoreGenerationHandlerConfiguration,
    ScoreGenerationStageHandler,
)
from datp_core.learning.training.handler import (
    ModelTrainingHandlerConfiguration,
    ModelTrainingStageHandler,
)
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.stages.analysis import StatisticalAnalysisStageHandler
from datp_core.reporting.audit.query import DuckDbAuditService
from datp_core.reporting.execution.freeze_handler import ResultFreezeStageHandler
from datp_core.reporting.execution.report_handler import ReportGenerationStageHandler
from datp_core.thresholding.calibration.handler import CalibrationSubsamplingStageHandler
from datp_core.thresholding.estimation.construction import ConstructThresholdsUseCase
from datp_core.thresholding.estimation.estimators import ESTIMATOR_KIND_REGISTRY
from datp_core.thresholding.estimation.ports import ThresholdEstimator
from datp_core.thresholding.execution.handler import ThresholdConstructionStageHandler


def _build_estimator_registry(
    config: ResolvedProjectConfiguration,
) -> TypedDomainRegistry[ThresholdPolicyId, ThresholdEstimator]:
    """Bind every estimator to its single resolved policy; no adapter-side policy values exist."""
    estimators: dict[ThresholdPolicyId, ThresholdEstimator] = {
        policy_id: ESTIMATOR_KIND_REGISTRY.create(policy_id, policy)
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


class _CommonConfigUseCases(BaseModel):
    """Configuration-layer use cases shared by both application variants."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

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


class ConfigOnlyApplication(BaseModel):
    """Lightweight composition root for configuration-only operations.

    Built from just YAML load + validate + resolve -- no artifact repository, no DuckDB
    service, no threshold estimators, no statistics adapter, no execution use case. Used by CLI
    commands that only read or explain configuration, so they never pay for the full
    application graph.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    config: ResolvedProjectConfiguration
    validate_configuration: ValidateProjectConfiguration
    describe_project: DescribeResolvedProject
    explain_authored_drift: ExplainAuthoredConfigurationDrift
    explain_scientific_drift: ExplainResolvedScientificDrift
    explain_execution_drift: ExplainExecutionConfigurationDrift
    fingerprint_config: FingerprintResolvedConfiguration


def build_config_only_application(
    config_dir: Path | None = None,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> ConfigOnlyApplication:
    """Factory composing only the configuration-layer use cases, with no infrastructure."""
    resolved_config = resolve_project_configuration(config_dir=config_dir, bootstrap_settings=bootstrap_settings)
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


class DatpApplication(BaseModel):
    """Composition root holding resolved configuration and injected use cases."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    config: ResolvedProjectConfiguration
    validate_configuration: ValidateProjectConfiguration
    describe_project: DescribeResolvedProject
    explain_authored_drift: ExplainAuthoredConfigurationDrift
    explain_scientific_drift: ExplainResolvedScientificDrift
    explain_execution_drift: ExplainExecutionConfigurationDrift
    fingerprint_config: FingerprintResolvedConfiguration
    audit_dataset: AuditDatasetUseCase
    execute_experiment: ExecuteExperimentUseCase
    run_experiment: ExperimentRunner
    run_campaign: CampaignRunner
    output_manager: ExperimentOutputManager
    construct_thresholds: ConstructThresholdsUseCase
    statistical_analysis: StatisticalAnalysisUseCase
    audit_svc: DuckDbAuditService
    plan_builder: ExperimentPlanBuilder

    def build_experiment_plan(
        self,
        experiment_id: ExperimentId,
    ) -> PlanningGraph:
        """Compile and build the execution plan for one experiment.

        This is the sole entry point for planning — the CLI commands ``experiment plan``
        and any other planning consumer must route through here rather than importing
        ``expand_experiment_jobs`` or ``ExperimentPlanBuilder`` directly.
        """
        from datp_core.experiments.planning.compilation import compile_experiment

        compiled = compile_experiment(self.config, experiment_id)
        return self.plan_builder.build(compiled)


def build_application(
    config_dir: Path | None = None,
    bootstrap_settings: RuntimeBootstrapSettings | None = None,
) -> DatpApplication:
    """Factory composing the entire DATP application graph without side effects on import."""
    resolved_config = resolve_project_configuration(config_dir=config_dir, bootstrap_settings=bootstrap_settings)

    cc = _build_common_config_use_cases(resolved_config)

    audit_ds = AuditDatasetUseCase()
    output_store = ArtifactStore(resolved_config.paths.outputs)
    adapter_registry = _build_adapter_registry()

    experiment_paths = ExperimentPaths(
        outputs_root=resolved_config.paths.outputs,
        repository_root=resolved_config.paths.repository_root,
    )
    plan_builder = ExperimentPlanBuilder(paths=experiment_paths)

    construct_th = ConstructThresholdsUseCase(
        config=resolved_config, registry=_build_estimator_registry(resolved_config)
    )
    statistical_analysis = StatisticalAnalysisUseCase(
        resolved_config.statistical_profiles,
    )
    executor = ExecuteExperimentUseCase(
        config=resolved_config,
        plan_builder=plan_builder,
        handlers=(
            PreflightStageHandler(resolved_config, output_store),
            DatasetMaterializationStageHandler(resolved_config, output_store, adapter_registry),
            ModelTrainingStageHandler(
                ModelTrainingHandlerConfiguration(
                    experiments=resolved_config.experiments,
                    training_profiles=resolved_config.training_profiles,
                    populations=resolved_config.populations,
                    datasets=resolved_config.datasets,
                    checkpoint_profiles=resolved_config.checkpoint_profiles,
                    model_architectures=resolved_config.model_architectures,
                    optimizers=resolved_config.optimizers,
                    batching_profiles=resolved_config.batching_profiles,
                    runtime=resolved_config.runtime,
                    protocol_determinism=resolved_config.protocol_determinism,
                ),
                output_store,
            ),
            CohortCheckpointSelectionStageHandler(resolved_config, output_store),
            ScoreGenerationStageHandler(
                ScoreGenerationHandlerConfiguration(
                    experiments=resolved_config.experiments,
                    training_profiles=resolved_config.training_profiles,
                    populations=resolved_config.populations,
                    datasets=resolved_config.datasets,
                    model_architectures=resolved_config.model_architectures,
                    batching_profiles=resolved_config.batching_profiles,
                    runtime=resolved_config.runtime,
                ),
                output_store,
            ),
            CalibrationSubsamplingStageHandler(resolved_config, output_store),
            ThresholdConstructionStageHandler(resolved_config, output_store, construct_th),
            OperatingPointEvaluationStageHandler(resolved_config, output_store),
            StatisticalAnalysisStageHandler(resolved_config, output_store, statistical_analysis),
            ResultFreezeStageHandler(resolved_config, output_store),
            ReportGenerationStageHandler(resolved_config, output_store),
        ),
    )
    output_manager = ExperimentOutputManager(resolved_config.paths.outputs)
    experiment_runner = ExperimentRunner(
        config=resolved_config,
        execute_experiment=executor,
        output_manager=output_manager,
    )
    campaign = CampaignRunner(
        config=resolved_config,
        plan_builder=plan_builder,
        execute_experiment=executor,
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
        run_experiment=experiment_runner,
        run_campaign=campaign,
        output_manager=output_manager,
        construct_thresholds=construct_th,
        statistical_analysis=statistical_analysis,
        audit_svc=audit_svc,
        plan_builder=plan_builder,
    )


__all__ = [
    "ConfigOnlyApplication",
    "ConfigurationError",
    "DatpApplication",
    "build_application",
    "build_config_only_application",
]
