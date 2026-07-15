from dataclasses import replace
from io import StringIO

from rich.console import Console

from datp_core.application.planning.planner import CreateExecutionPlanRequest, expand_cells
from datp_core.cli.main import invoke_command
from datp_core.composition.root import (
    BoundaryExitCode,
    CompositionCommandSuccess,
    RunExperimentRequest,
)
from datp_core.domain.experiments.feasibility import ScientificReadinessResult
from datp_core.domain.runtime.policies import PipelineStage
from tests.support.runtime_orchestration import runtime_preflight_request
from tests.unit.cli.test_main import SyntheticCompositionUseCase
from tests.unit.composition.test_registries import RecordingStageRunner, synthetic_root


def test_synthetic_socle_runs_the_complete_declared_stage_sequence_and_cli_boundary() -> None:
    runner = RecordingStageRunner()
    root = synthetic_root(runner=runner)
    planning_request = CreateExecutionPlanRequest(
        specifications=(root.configuration.experiment,),
        scientific_readiness=ScientificReadinessResult(blockers=()),
    )
    draft = root.create_plan(planning_request)
    cell = expand_cells(request=planning_request)[0]
    preflight = root.validate_execution(replace(runtime_preflight_request(), draft=draft))
    plan = replace(
        preflight.final_plan,
        stages=tuple(stage for stage in preflight.final_plan.stages if stage.cell_id == cell.cell_id),
    )
    output = StringIO()
    console = Console(file=output, color_system=None)

    summary = root.run_experiment(RunExperimentRequest(cell=cell, final_plan=plan))
    exit_code = invoke_command(
        arguments=("run",),
        use_case=SyntheticCompositionUseCase(result=CompositionCommandSuccess(message="synthetic socle complete")),
        console=console,
    )

    assert summary.failed == ()
    assert tuple(runner.executed) == tuple(stage.stage for stage in plan.stages)
    assert tuple(runner.executed) == tuple(PipelineStage)
    assert exit_code is BoundaryExitCode.SUCCESS
    assert output.getvalue().strip() == "synthetic socle complete"
