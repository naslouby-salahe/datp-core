from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import Protocol

from datp_core.application.planning.gates import AnchorReproductionGate, FeasibilityGateEvaluator
from datp_core.application.planning.plan import DraftExecutionPlan
from datp_core.application.planning.planner import CreateExecutionPlanRequest, ExperimentPlanner
from datp_core.application.planning.reuse import ScoreReuseGate
from datp_core.application.ports.data import (
    ClientPartitioner,
    DatasetSourceInspector,
    PreprocessorFitter,
    ProcessedSplitMaterializer,
    SplitManifestBuilder,
)
from datp_core.application.ports.learning import CentralizedModelTrainer, FederatedTrainer
from datp_core.application.ports.persistence import (
    ArtifactLockProvider,
    ArtifactStore,
    CheckpointStore,
    ManifestStore,
    RunStateStore,
)
from datp_core.application.ports.reporting import ReportRenderer
from datp_core.application.ports.runtime import (
    Clock,
    CodeStateProvider,
    CudaGuard,
    DependencyLockStateProvider,
    EnvironmentInventoryProvider,
    HardwareInspector,
    ResourcePressureMonitor,
)
from datp_core.application.ports.scoring import ScoreGenerator
from datp_core.application.ports.statistics import StatisticalProcedureRunner
from datp_core.application.ports.telemetry import EventSink
from datp_core.application.reporting.tracing import TableFigureTracer
from datp_core.application.runtime.executor import ExecuteFinalPlanRequest, ExecutionSummary, PlanExecutor
from datp_core.application.runtime.preflight import (
    ExecutionPreflight,
    FinalExecutionPlan,
    PreflightRequest,
    PreflightResult,
)
from datp_core.application.stages.evaluate_policy import PolicyEvaluator
from datp_core.application.stages.select_checkpoint import CheckpointSelector
from datp_core.composition.registries import (
    StageRunnerRegistry,
    ThresholdStrategyCollaborators,
    ThresholdStrategyRegistry,
    build_threshold_strategy_registry,
)
from datp_core.config.resolved import ResolvedConfigurationArtifact
from datp_core.domain.errors import (
    AmbiguousPlanError,
    AnchorReproductionFailure,
    ArtifactError,
    ArtifactLockConflict,
    CheckpointError,
    CheckpointSelectionError,
    ClientUpdateError,
    ConfigurationError,
    CudaDeviceMismatchError,
    CudaOutOfMemoryError,
    CudaUnavailableError,
    CyclicPlanError,
    DatasetError,
    DatpCoreError,
    DeterminismViolationError,
    DiskSpaceError,
    DomainValidationError,
    EnvironmentIncompatibilityError,
    EvaluationError,
    FeasibilityRejection,
    FullParticipationViolationError,
    InvalidCpuFallbackError,
    PathResolutionError,
    PreprocessingError,
    ProvenanceError,
    RamPreflightError,
    RecoveryStateMismatchError,
    ReportingError,
    ResourceBudgetExceededError,
    ReuseBlockedError,
    ReuseIncompatibilityError,
    ScoringError,
    StageFingerprintMismatchError,
    StatisticsError,
    TestProfileValidationError,
    ThresholdError,
    TrainingError,
    UnsafeParallelismError,
)
from datp_core.domain.experiments.specifications import ExperimentCell, ExperimentSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class DataPortBindings:
    source_inspector: DatasetSourceInspector
    client_partitioner: ClientPartitioner
    split_manifest_builder: SplitManifestBuilder
    preprocessor_fitter: PreprocessorFitter
    processed_split_materializer: ProcessedSplitMaterializer


@dataclass(frozen=True, slots=True, kw_only=True)
class LearningPortBindings:
    federated_trainer: FederatedTrainer
    centralized_trainer: CentralizedModelTrainer
    score_generator: ScoreGenerator


@dataclass(frozen=True, slots=True, kw_only=True)
class PersistencePortBindings:
    artifact_store: ArtifactStore
    checkpoint_store: CheckpointStore
    manifest_store: ManifestStore
    run_state_store: RunStateStore
    lock_provider: ArtifactLockProvider


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimePortBindings:
    hardware_inspector: HardwareInspector
    cuda_guard: CudaGuard
    resource_pressure_monitor: ResourcePressureMonitor
    code_state_provider: CodeStateProvider
    dependency_lock_state_provider: DependencyLockStateProvider
    environment_inventory_provider: EnvironmentInventoryProvider
    clock: Clock


@dataclass(frozen=True, slots=True, kw_only=True)
class OutputPortBindings:
    statistics_runner: StatisticalProcedureRunner
    markdown_renderer: ReportRenderer
    latex_renderer: ReportRenderer
    figure_renderer: ReportRenderer
    event_sink: EventSink


@dataclass(frozen=True, slots=True, kw_only=True)
class CompositionPortBindings:
    data: DataPortBindings
    learning: LearningPortBindings
    persistence: PersistencePortBindings
    runtime: RuntimePortBindings
    output: OutputPortBindings


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedExperimentConfiguration:
    resolved: ResolvedConfigurationArtifact
    experiment: ExperimentSpec

    def __post_init__(self) -> None:
        if (
            self.experiment.scientific_protocol != self.resolved.scientific
            or self.experiment.execution_policy != self.resolved.execution
        ):
            raise DomainValidationError(
                detail="composition configuration must retain the resolved scientific and execution specifications",
                value=repr(self.experiment.identity.experiment_id),
                constraint="ExperimentSpec agrees with ResolvedConfigurationArtifact",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ComposeApplicationRequest:
    configuration: ResolvedExperimentConfiguration
    ports: CompositionPortBindings
    stage_runners: StageRunnerRegistry
    threshold_collaborators: ThresholdStrategyCollaborators


@dataclass(frozen=True, slots=True, kw_only=True)
class ComposedApplicationServices:
    experiment_planner: ExperimentPlanner
    execution_preflight: ExecutionPreflight
    score_reuse_gate: ScoreReuseGate
    checkpoint_selector: CheckpointSelector
    policy_evaluator: PolicyEvaluator
    anchor_reproduction_gate: AnchorReproductionGate
    feasibility_gate_evaluator: FeasibilityGateEvaluator
    plan_executor: PlanExecutor
    table_figure_tracer: TableFigureTracer
    threshold_registry: ThresholdStrategyRegistry


@dataclass(frozen=True, slots=True, kw_only=True)
class RunExperimentRequest:
    cell: ExperimentCell
    final_plan: FinalExecutionPlan


class CompositionCommand(StrEnum):
    RUN = "run"


class BoundaryExitCode(IntEnum):
    SUCCESS = 0
    CONFIGURATION = 2
    DOMAIN_VALIDATION = 3
    DATASET = 4
    PREPROCESSING = 5
    CUDA = 6
    RESOURCE = 7
    TRAINING = 8
    CHECKPOINT = 9
    SCORING = 10
    THRESHOLD = 11
    ANCHOR_REPRODUCTION = 12
    EVALUATION = 13
    STATISTICS = 14
    ARTIFACT = 15
    ARTIFACT_LOCK = 16
    PATH_RESOLUTION = 17
    PROVENANCE = 18
    REUSE = 19
    DETERMINISM = 20
    FEASIBILITY = 21
    PLAN = 22
    TEST_PROFILE = 23
    ENVIRONMENT = 24
    REPORTING = 25


@dataclass(frozen=True, slots=True, kw_only=True)
class RunCompositionCommandRequest:
    command: CompositionCommand


@dataclass(frozen=True, slots=True, kw_only=True)
class CompositionCommandSuccess:
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class CompositionCommandFailure:
    error: DatpCoreError

    @property
    def exit_code(self) -> BoundaryExitCode:
        return error_exit_code(self.error)


type CompositionCommandResult = CompositionCommandSuccess | CompositionCommandFailure


class CompositionCommandUseCase(Protocol):
    def execute_command(self, request: RunCompositionCommandRequest) -> CompositionCommandResult: ...


@dataclass(frozen=True, slots=True)
class PhaseOneCommandUseCase:
    def execute_command(self, request: RunCompositionCommandRequest) -> CompositionCommandResult:
        if request.command is not CompositionCommand.RUN:
            raise DomainValidationError(
                detail="composition command must be declared by the composition boundary",
                value=repr(request.command),
                constraint="CompositionCommand.RUN",
            )
        return CompositionCommandFailure(
            error=ConfigurationError(
                detail="a command-executable composition requires explicit typed port bindings",
                section="composition",
                field="ports",
                mode="run",
            )
        )


PHASE_ONE_COMMAND_USE_CASE = PhaseOneCommandUseCase()


def error_exit_code(error: DatpCoreError) -> BoundaryExitCode:
    match error:
        case ConfigurationError():
            return BoundaryExitCode.CONFIGURATION
        case DomainValidationError():
            return BoundaryExitCode.DOMAIN_VALIDATION
        case DatasetError():
            return BoundaryExitCode.DATASET
        case PreprocessingError():
            return BoundaryExitCode.PREPROCESSING
        case CudaUnavailableError() | CudaDeviceMismatchError() | CudaOutOfMemoryError():
            return BoundaryExitCode.CUDA
        case (
            RamPreflightError()
            | ResourceBudgetExceededError()
            | DiskSpaceError()
            | UnsafeParallelismError()
            | InvalidCpuFallbackError()
        ):
            return BoundaryExitCode.RESOURCE
        case TrainingError() | ClientUpdateError() | FullParticipationViolationError():
            return BoundaryExitCode.TRAINING
        case CheckpointError() | CheckpointSelectionError() | RecoveryStateMismatchError():
            return BoundaryExitCode.CHECKPOINT
        case ScoringError():
            return BoundaryExitCode.SCORING
        case ThresholdError():
            return BoundaryExitCode.THRESHOLD
        case AnchorReproductionFailure():
            return BoundaryExitCode.ANCHOR_REPRODUCTION
        case EvaluationError():
            return BoundaryExitCode.EVALUATION
        case StatisticsError():
            return BoundaryExitCode.STATISTICS
        case ArtifactError() | StageFingerprintMismatchError():
            return BoundaryExitCode.ARTIFACT
        case ArtifactLockConflict():
            return BoundaryExitCode.ARTIFACT_LOCK
        case PathResolutionError():
            return BoundaryExitCode.PATH_RESOLUTION
        case ProvenanceError():
            return BoundaryExitCode.PROVENANCE
        case ReuseIncompatibilityError() | ReuseBlockedError():
            return BoundaryExitCode.REUSE
        case DeterminismViolationError():
            return BoundaryExitCode.DETERMINISM
        case FeasibilityRejection():
            return BoundaryExitCode.FEASIBILITY
        case AmbiguousPlanError() | CyclicPlanError():
            return BoundaryExitCode.PLAN
        case TestProfileValidationError():
            return BoundaryExitCode.TEST_PROFILE
        case EnvironmentIncompatibilityError():
            return BoundaryExitCode.ENVIRONMENT
        case ReportingError():
            return BoundaryExitCode.REPORTING
        case _:
            raise TypeError(f"no process exit code is declared for {type(error).__name__}")


@dataclass(frozen=True, slots=True, kw_only=True)
class CompositionRoot:
    configuration: ResolvedExperimentConfiguration
    ports: CompositionPortBindings
    services: ComposedApplicationServices

    def create_plan(self, request: CreateExecutionPlanRequest) -> DraftExecutionPlan:
        return self.services.experiment_planner.create_plan(request)

    def validate_execution(self, request: PreflightRequest) -> PreflightResult:
        return self.services.execution_preflight.validate(request)

    def run_experiment(self, request: RunExperimentRequest) -> ExecutionSummary:
        _validate_execution_cell(request)
        return self.services.plan_executor.execute(ExecuteFinalPlanRequest(plan=request.final_plan))


def compose_application(request: ComposeApplicationRequest) -> CompositionRoot:
    threshold_registry = build_threshold_strategy_registry(request.threshold_collaborators)
    return CompositionRoot(
        configuration=request.configuration,
        ports=request.ports,
        services=ComposedApplicationServices(
            experiment_planner=ExperimentPlanner(),
            execution_preflight=ExecutionPreflight(),
            score_reuse_gate=ScoreReuseGate(),
            checkpoint_selector=CheckpointSelector(),
            policy_evaluator=PolicyEvaluator(),
            anchor_reproduction_gate=AnchorReproductionGate(),
            feasibility_gate_evaluator=FeasibilityGateEvaluator(),
            plan_executor=request.stage_runners.create_executor(),
            table_figure_tracer=TableFigureTracer(),
            threshold_registry=threshold_registry,
        ),
    )


def _validate_execution_cell(request: RunExperimentRequest) -> None:
    if not request.final_plan.stages or any(
        stage.cell_id != request.cell.cell_id for stage in request.final_plan.stages
    ):
        raise DomainValidationError(
            detail="composed execution plan must contain stages for exactly one experiment cell",
            value=repr(tuple(stage.cell_id for stage in request.final_plan.stages)),
            constraint="every FinalPlannedStage cell_id matches RunExperimentRequest.cell",
        )
