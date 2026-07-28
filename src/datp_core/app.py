"""DatpApplication composition root assembling every feature package's use cases and stage
handlers -- the sole module in the codebase permitted to import concrete infrastructure across
package boundaries.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from datp_core.analysis.calibration.conformal import analyze_conformal_coverage
from datp_core.analysis.calibration.quantile import analyze_quantile_estimation
from datp_core.analysis.calibration.stability import analyze_threshold_stability
from datp_core.analysis.clustering.membership import analyze_cluster_stability
from datp_core.analysis.comparisons.association import analyze_association
from datp_core.analysis.comparisons.effect_ratios import analyze_absorption, analyze_recovery_fraction
from datp_core.analysis.comparisons.paired import analyze_paired
from datp_core.analysis.mechanisms.distributions import (
    analyze_distribution_mechanism,
    analyze_locked_client_distribution,
)
from datp_core.analysis.mechanisms.operational import analyze_alert_burden, analyze_resource_cost
from datp_core.analysis.mechanisms.temporal import analyze_temporal_recovery
from datp_core.analysis.runtime.runner import AnalysisHandlerRegistry
from datp_core.analysis.statistics.inference import StatisticalAnalysisUseCase
from datp_core.analysis.validation import analyze_anchor_equivalence
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
from datp_core.core.identifiers import ExperimentId
from datp_core.data.adapters.ciciot2023.adapter import CICIoT2023Adapter
from datp_core.data.adapters.edge_iiotset.adapter import EdgeIIoTsetAdapter
from datp_core.data.adapters.nbaiot.adapter import NBaIoTAdapter
from datp_core.data.contracts.dataset import ResolvedDataset
from datp_core.data.materialization.handler import DatasetMaterializationStageHandler
from datp_core.data.materialization.registry import DatasetAdapterRegistry
from datp_core.data.readiness.materialized import assess_materialized_readiness
from datp_core.data.readiness.models import build_readiness_report
from datp_core.data.readiness.source import assess_source_readiness
from datp_core.data.sources.inventory import build_source_inventory
from datp_core.evaluation.stage import OperatingPointEvaluationStageHandler
from datp_core.experiments.catalogue.analyses import AnalysisKind
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
from datp_core.thresholding.engine import ThresholdEngine
from datp_core.thresholding.stages import (
    CalibrationSubsamplingStageHandler,
    ThresholdConstructionStageHandler,
)


def _build_threshold_engine() -> ThresholdEngine:
    """Create the threshold engine — no registry, no estimator classes, pure dispatch."""
    return ThresholdEngine()


def _build_adapter_registry() -> DatasetAdapterRegistry:
    """Build the adapter registry with one adapter per supported AdapterKind."""
    return DatasetAdapterRegistry(
        adapters=(
            NBaIoTAdapter(),
            CICIoT2023Adapter(),
            EdgeIIoTsetAdapter(),
        )
    )


def _build_analysis_registry() -> AnalysisHandlerRegistry:
    """Build the analysis handler registry with all 14 capability handlers."""
    registry = AnalysisHandlerRegistry()
    registry.register(AnalysisKind.PAIRED_THRESHOLD, analyze_paired)
    registry.register(AnalysisKind.ABSORPTION, analyze_absorption)
    registry.register(AnalysisKind.ALERT_BURDEN, analyze_alert_burden)
    registry.register(AnalysisKind.ANCHOR_EQUIVALENCE, analyze_anchor_equivalence)
    registry.register(AnalysisKind.CLUSTER_STABILITY, analyze_cluster_stability)
    registry.register(AnalysisKind.CONFORMAL_COVERAGE, analyze_conformal_coverage)
    registry.register(AnalysisKind.DISTRIBUTION_MECHANISM, analyze_distribution_mechanism)
    registry.register(AnalysisKind.LOCKED_CLIENT_DISTRIBUTION, analyze_locked_client_distribution)
    registry.register(AnalysisKind.METRIC_ASSOCIATION, analyze_association)
    registry.register(AnalysisKind.QUANTILE_ESTIMATION, analyze_quantile_estimation)
    registry.register(AnalysisKind.RECOVERY_FRACTION, analyze_recovery_fraction)
    registry.register(AnalysisKind.RESOURCE_COST, analyze_resource_cost)
    registry.register(AnalysisKind.TEMPORAL_RECOVERY, analyze_temporal_recovery)
    registry.register(AnalysisKind.THRESHOLD_STABILITY, analyze_threshold_stability)
    return registry


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
    service, no threshold estimators, no statistics adapter, no execution use case.
    """

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    config: ResolvedProjectConfiguration
    validate_configuration: ValidateProjectConfiguration
    describe_project: DescribeResolvedProject
    explain_authored_drift: ExplainAuthoredConfigurationDrift
    explain_scientific_drift: ExplainResolvedScientificDrift
    explain_execution_drift: ExplainExecutionConfigurationDrift
    fingerprint_config: FingerprintResolvedConfiguration

    def explain_scientific_drift_between_dirs(
        self,
        current_config_dir: Path,
        expected_config_dir: Path,
    ):
        current = resolve_project_configuration(config_dir=current_config_dir)
        expected = resolve_project_configuration(config_dir=expected_config_dir)
        return self.explain_scientific_drift.execute(current_config=current, expected_config=expected)

    def explain_execution_drift_between_dirs(
        self,
        current_config_dir: Path,
        expected_config_dir: Path,
    ):
        current = resolve_project_configuration(config_dir=current_config_dir)
        expected = resolve_project_configuration(config_dir=expected_config_dir)
        return self.explain_execution_drift.execute(current_config=current, expected_config=expected)


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


class _AuditResult:
    """Minimal result providing raw_source_found / file_count for the CLI audit command."""
    __slots__ = ("raw_source_found", "file_count")

    def __init__(self, raw_source_found: bool, file_count: int) -> None:
        self.raw_source_found = raw_source_found
        self.file_count = file_count


class AuditDatasetUseCase:
    """Replacement for the deleted readiness use case — wraps standalone readiness functions."""
    __slots__ = ("_config",)

    def __init__(self, config: ResolvedProjectConfiguration) -> None:
        self._config = config

    def execute(self, dataset: ResolvedDataset) -> _AuditResult:
        inventory = build_source_inventory(
            dataset_id=dataset.dataset_id,
            raw_data_root=dataset.paths.raw_data_root,
            source=dataset.source,
        )
        report = assess_source_readiness(dataset.source, inventory)
        total = sum(audit.file_count for audit in report.tree_audits)
        return _AuditResult(raw_source_found=total > 0, file_count=total)


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
    construct_thresholds: ThresholdEngine
    statistical_analysis: StatisticalAnalysisUseCase
    audit_svc: DuckDbAuditService
    plan_builder: ExperimentPlanBuilder
    paths: ExperimentPaths

    def run_diagnostic_experiment(
        self,
        experiment: str,
        *,
        seed_index: int = 0,
        profile: str = "smoke",
    ):
        from datp_core.orchestration.diagnostics import run_experiment_diagnostic

        _ = profile
        return run_experiment_diagnostic(experiment, self, seed_index=seed_index)

    def run_diagnostic_campaign(self, *, profile: str = "smoke"):
        from datp_core.orchestration.diagnostics import run_campaign_diagnostic

        _ = profile
        return run_campaign_diagnostic(self)

    def execute_dagster_experiment(self, experiment: str):
        from datp_core.orchestration.dagster_defs import build_dagster_definitions

        defs = build_dagster_definitions(self)
        job_name = f"datp_{experiment}"
        job = defs.get_job_def(job_name)
        return job.execute_in_process() if job is not None else None

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

    audit_ds = AuditDatasetUseCase(config=resolved_config)
    output_store = ArtifactStore(resolved_config.paths.outputs)
    adapter_registry = _build_adapter_registry()

    experiment_paths = ExperimentPaths(
        outputs_root=resolved_config.paths.outputs,
        repository_root=resolved_config.paths.repository_root,
    )
    plan_builder = ExperimentPlanBuilder(paths=experiment_paths)

    construct_th = _build_threshold_engine()
    statistical_analysis = StatisticalAnalysisUseCase(
        resolved_config.statistical_profiles,
    )
    analysis_registry = _build_analysis_registry()
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
            OperatingPointEvaluationStageHandler(output_store),
            StatisticalAnalysisStageHandler(resolved_config, output_store, statistical_analysis, analysis_registry),
            ResultFreezeStageHandler(resolved_config, output_store),
            ReportGenerationStageHandler(output_store),
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
        paths=experiment_paths,
    )


__all__ = [
    "ConfigOnlyApplication",
    "ConfigurationError",
    "DatpApplication",
    "build_application",
    "build_config_only_application",
]
