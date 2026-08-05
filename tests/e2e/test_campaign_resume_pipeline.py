from pathlib import Path

from datp_core.domain.enums import ExperimentId
from datp_core.domain.values import Seed
from datp_core.pipeline.execution.engine import build_campaign, execute_campaign, resolve_execution_recipe
from datp_core.pipeline.execution.models import (
    CampaignPlan,
    ExistingExperimentState,
    PipelineStage,
    StageExecution,
    StageOutcome,
)
from datp_core.pipeline.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.protocols.experiments import EXPERIMENTS
from datp_core.protocols.models import SeedCohort


class _IncompleteStore:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def state(self, coordinate, output_root: Path) -> ExistingExperimentState:
        del coordinate, output_root
        return ExistingExperimentState.INCOMPLETE

    def delete(self, coordinate, output_root: Path) -> None:
        del output_root
        self.deleted.append(coordinate.stable_key)


class _CompleteStore:
    def __init__(self) -> None:
        self.deleted: list[str] = []

    def state(self, coordinate, output_root: Path) -> ExistingExperimentState:
        del coordinate, output_root
        return ExistingExperimentState.COMPLETE_VALID

    def delete(self, coordinate, output_root: Path) -> None:
        del output_root
        self.deleted.append(coordinate.stable_key)


class _SuccessfulRunner:
    def __init__(self) -> None:
        self.stages: list[PipelineStage] = []
        self.output_roots: list[Path] = []

    def run(self, stage: PipelineStage, coordinate, provenance, output_root: Path) -> StageExecution:
        del coordinate, provenance
        self.stages.append(stage)
        self.output_roots.append(output_root)
        return StageExecution(stage=stage, outcome=StageOutcome.COMPLETED, evidence="tiny deterministic fixture")


def _tiny_campaign() -> CampaignPlan:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason="tiny campaign fixture is available",
            ),
        ),
    )
    return build_campaign(plan)


def test_campaign_resume_deletes_incomplete_cells_and_restarts_in_canonical_order(tmp_path: Path) -> None:
    campaign = _tiny_campaign()
    store = _IncompleteStore()
    runner = _SuccessfulRunner()

    result = execute_campaign(
        campaign=campaign,
        stage_runner=runner,
        output_store=store,
        output_root=tmp_path,
    )

    assert result.campaign_digest == campaign.digest
    assert all(execution.successful for execution in result.experiments)
    assert len(store.deleted) == len(campaign.entries)
    recipe_stages = resolve_execution_recipe(campaign.entries[0].coordinate).stages
    assert tuple(runner.stages) == recipe_stages * len(campaign.entries)
    assert set(runner.output_roots) == {tmp_path}


def test_repeated_tiny_campaigns_have_identical_plan_execution_and_cleanup(tmp_path: Path) -> None:
    campaign = _tiny_campaign()
    first_store = _IncompleteStore()
    second_store = _IncompleteStore()
    first_runner = _SuccessfulRunner()
    second_runner = _SuccessfulRunner()
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first = execute_campaign(
        campaign=campaign,
        stage_runner=first_runner,
        output_store=first_store,
        output_root=first_root,
    )
    second = execute_campaign(
        campaign=campaign,
        stage_runner=second_runner,
        output_store=second_store,
        output_root=second_root,
    )

    assert campaign == _tiny_campaign()
    assert first == second
    assert first_store.deleted == second_store.deleted
    assert first_runner.stages == second_runner.stages
    assert set(first_runner.output_roots) == {first_root}
    assert set(second_runner.output_roots) == {second_root}


def test_complete_campaign_cells_are_reused_without_stage_execution(tmp_path: Path) -> None:
    campaign = _tiny_campaign()
    store = _CompleteStore()
    runner = _SuccessfulRunner()

    result = execute_campaign(
        campaign=campaign,
        stage_runner=runner,
        output_store=store,
        output_root=tmp_path,
    )

    assert all(execution.successful for execution in result.experiments)
    assert all(execution.reused_complete_experiment for execution in result.experiments)
    assert not runner.stages
    assert not runner.output_roots
    assert not store.deleted
