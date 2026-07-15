from dataclasses import replace
from inspect import signature
from typing import NoReturn, overload

import pytest
from tests.support.runtime_orchestration import runtime_preflight_request
from tests.unit.config.test_mapping import experiment_config

from datp_core.application.planning.planner import (
    CreateExecutionPlanRequest,
    expand_cells,
)
from datp_core.application.runtime.executor import StageRunner
from datp_core.application.runtime.preflight import FinalPlannedStage
from datp_core.composition.registries import (
    StageRunnerRegistry,
    ThresholdStrategyCollaborators,
    build_threshold_strategy_registry,
)
from datp_core.composition.root import (
    ComposeApplicationRequest,
    CompositionPortBindings,
    DataPortBindings,
    LearningPortBindings,
    OutputPortBindings,
    PersistencePortBindings,
    ResolvedExperimentConfiguration,
    RunExperimentRequest,
    RuntimePortBindings,
    compose_application,
)
from datp_core.config.mapping.scientific import map_experiment_schema
from datp_core.config.resolved import ResolvedConfigurationArtifact
from datp_core.domain.artifacts.keys import StorageRootKind
from datp_core.domain.artifacts.lineage import ResolvedConfigurationIdentity
from datp_core.domain.artifacts.references import ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.feasibility import ScientificReadinessResult
from datp_core.domain.experiments.specification_changes import EnvironmentSpecification, StorageRootDescriptor
from datp_core.domain.runtime.policies import ExecutionMode, PipelineStage
from datp_core.domain.runtime.seeds import EnumMap, EnumMapEntry
from datp_core.domain.thresholding.policies import ThresholdConstructionKind


class _UnavailableCollaborator:
    def read(self, **kwargs: object) -> NoReturn:
        del kwargs
        raise AssertionError("registry construction must not read scores")

    def members(self, **kwargs: object) -> NoReturn:
        del kwargs
        raise AssertionError("registry construction must not read memberships")


class _NoopStageRunner(StageRunner):
    def run(self, stage: FinalPlannedStage) -> None:
        del stage


class RecordingStageRunner(StageRunner):
    def __init__(self) -> None:
        self.executed: list[PipelineStage] = []

    def run(self, stage: FinalPlannedStage) -> None:
        self.executed.append(stage.stage)


class _UnavailablePort:
    def acquire(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def append(self, record: object) -> NoReturn:
        del record
        raise AssertionError("the composition construction test must not invoke a port")

    def build(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def commit_bundle(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def find_compatible(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def fit(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def generate_calibration_scores(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def generate_temporal_scores(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def generate_test_scores(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def inspect(self, request: object | None = None) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def load_recovery(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def lookup(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def materialize(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def now(self) -> NoReturn:
        raise AssertionError("the composition construction test must not invoke a port")

    def partition(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def publish(self, event: object) -> NoReturn:
        del event
        raise AssertionError("the composition construction test must not invoke a port")

    def record(self, manifest: object) -> NoReturn:
        del manifest
        raise AssertionError("the composition construction test must not invoke a port")

    @overload
    def read(self, *, calibration_scores: object, client_index: int) -> NoReturn: ...

    @overload
    def read(self, *, assignment_identity: str) -> NoReturn: ...

    def read(self, **arguments: object) -> NoReturn:
        del arguments
        raise AssertionError("the composition construction test must not invoke a port")

    def render(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def require_cuda(self, device: object) -> NoReturn:
        del device
        raise AssertionError("the composition construction test must not invoke a port")

    def run(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def save(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def save_recovery(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def status_of(self, stage_fingerprint: object) -> NoReturn:
        del stage_fingerprint
        raise AssertionError("the composition construction test must not invoke a port")

    def trace(self, output_id: str) -> NoReturn:
        del output_id
        raise AssertionError("the composition construction test must not invoke a port")

    def validate_integrity(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def write_atomically(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")

    def members(self, *, family_manifest: str, client_id: object) -> NoReturn:
        del family_manifest, client_id
        raise AssertionError("the composition construction test must not invoke a port")

    def train(self, request: object) -> NoReturn:
        del request
        raise AssertionError("the composition construction test must not invoke a port")


def _configuration() -> ResolvedExperimentConfiguration:
    experiment = map_experiment_schema(experiment_config())
    return ResolvedExperimentConfiguration(
        resolved=ResolvedConfigurationArtifact(
            identity=ResolvedConfigurationIdentity(value=StageFingerprint(value="a" * 64)),
            schema_version=ArtifactSchemaVersion(value="v1"),
            scientific=experiment.scientific_protocol,
            execution=experiment.execution_policy,
            environment=EnvironmentSpecification(
                storage_roots=(StorageRootDescriptor(kind=StorageRootKind.SCORES, descriptor="synthetic"),)
            ),
        ),
        experiment=experiment,
    )


def synthetic_root(*, runner: StageRunner):
    port = _UnavailablePort()
    stages = tuple(PipelineStage)
    stage_runners = StageRunnerRegistry(
        runners=EnumMap(
            entries=tuple(EnumMapEntry(key=stage, value=runner) for stage in stages),
            allowed_keys=stages,
            is_sparse=False,
        )
    )
    bindings = CompositionPortBindings(
        data=DataPortBindings(
            source_inspector=port,
            client_partitioner=port,
            split_manifest_builder=port,
            preprocessor_fitter=port,
            processed_split_materializer=port,
        ),
        learning=LearningPortBindings(
            federated_trainer=port,
            centralized_trainer=port,
            score_generator=port,
        ),
        persistence=PersistencePortBindings(
            artifact_store=port,
            checkpoint_store=port,
            manifest_store=port,
            run_state_store=port,
            lock_provider=port,
        ),
        runtime=RuntimePortBindings(
            hardware_inspector=port,
            cuda_guard=port,
            resource_pressure_monitor=port,
            code_state_provider=port,
            dependency_lock_state_provider=port,
            environment_inventory_provider=port,
            clock=port,
        ),
        output=OutputPortBindings(
            statistics_runner=port,
            markdown_renderer=port,
            latex_renderer=port,
            figure_renderer=port,
            event_sink=port,
        ),
    )
    return compose_application(
        ComposeApplicationRequest(
            configuration=_configuration(),
            ports=bindings,
            stage_runners=stage_runners,
            threshold_collaborators=ThresholdStrategyCollaborators(
                calibration_scores=port,
                family_memberships=port,
                cluster_assignments=port,
            ),
        )
    )


def test_threshold_strategy_registry_is_exhaustive_and_excludes_centralized_b0() -> None:
    collaborator = _UnavailableCollaborator()

    registry = build_threshold_strategy_registry(
        ThresholdStrategyCollaborators(
            calibration_scores=collaborator,
            family_memberships=collaborator,
            cluster_assignments=collaborator,
        )
    )

    assert tuple(entry.key for entry in registry.strategies.entries) == tuple(ThresholdConstructionKind)
    assert registry.constructor.shared is registry.strategies.entries[0].value
    assert registry.constructor.local is registry.strategies.entries[1].value
    assert registry.constructor.family is registry.strategies.entries[2].value
    assert registry.constructor.cluster is registry.strategies.entries[3].value


def test_registered_threshold_strategies_satisfy_their_declared_port_operations() -> None:
    collaborator = _UnavailableCollaborator()
    registry = build_threshold_strategy_registry(
        ThresholdStrategyCollaborators(
            calibration_scores=collaborator,
            family_memberships=collaborator,
            cluster_assignments=collaborator,
        )
    )

    assert all(tuple(signature(entry.value.assign).parameters) == ("request",) for entry in registry.strategies.entries)
    assert tuple(signature(registry.quantile_estimator.estimate).parameters) == ("request",)
    assert tuple(signature(registry.clustering_strategy.cluster).parameters) == ("request",)


def test_stage_runner_registry_rejects_a_nonexhaustive_map_at_construction() -> None:
    with pytest.raises(DomainValidationError, match="non-sparse enum map must be exhaustive"):
        EnumMap(
            entries=(EnumMapEntry(key=PipelineStage.SOURCE_INSPECTION, value=_NoopStageRunner()),),
            allowed_keys=tuple(PipelineStage),
            is_sparse=False,
        )


def test_stage_runner_registry_rejects_a_reordered_map_at_construction() -> None:
    stages = tuple(PipelineStage)
    reversed_stages = tuple(reversed(stages))
    runners = EnumMap(
        entries=tuple(EnumMapEntry(key=stage, value=_NoopStageRunner()) for stage in reversed_stages),
        allowed_keys=reversed_stages,
        is_sparse=False,
    )

    with pytest.raises(DomainValidationError, match="declared order"):
        StageRunnerRegistry(runners=runners)


def test_stage_runner_registry_constructs_an_executor_from_every_pipeline_stage() -> None:
    stages = tuple(PipelineStage)
    registry = StageRunnerRegistry(
        runners=EnumMap(
            entries=tuple(EnumMapEntry(key=stage, value=_NoopStageRunner()) for stage in stages),
            allowed_keys=stages,
            is_sparse=False,
        )
    )

    executor = registry.create_executor()

    assert executor is not None


def test_composition_root_binds_every_port_and_constructs_every_application_service() -> None:
    root = synthetic_root(runner=_NoopStageRunner())

    assert root.configuration.experiment is not None
    assert root.services.plan_executor is not None
    assert root.services.threshold_registry.constructor is not None


def test_composition_configuration_rejects_a_resolved_execution_mismatch() -> None:
    configuration = _configuration()

    with pytest.raises(DomainValidationError, match="must retain the resolved scientific and execution"):
        ResolvedExperimentConfiguration(
            resolved=replace(
                configuration.resolved,
                execution=replace(configuration.resolved.execution, execution_mode=ExecutionMode.SMOKE),
            ),
            experiment=configuration.experiment,
        )


def test_composed_root_runs_one_synthetic_cell_through_the_complete_stage_registry() -> None:
    runner = RecordingStageRunner()
    root = synthetic_root(runner=runner)
    planning_request = CreateExecutionPlanRequest(
        specifications=(root.configuration.experiment,),
        scientific_readiness=ScientificReadinessResult(blockers=()),
    )
    draft = root.create_plan(planning_request)
    cell = expand_cells(request=planning_request)[0]
    preflight = root.validate_execution(replace(runtime_preflight_request(), draft=draft))
    single_cell_plan = replace(
        preflight.final_plan,
        stages=tuple(stage for stage in preflight.final_plan.stages if stage.cell_id == cell.cell_id),
    )

    summary = root.run_experiment(RunExperimentRequest(cell=cell, final_plan=single_cell_plan))

    assert summary.failed == ()
    assert tuple(runner.executed) == tuple(stage.stage for stage in single_cell_plan.stages)
