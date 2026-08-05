from pathlib import Path

from datp_core.domain.enums import ExperimentId
from datp_core.domain.values import Seed
from datp_core.pipeline.campaign import build_campaign, execute_campaign
from datp_core.pipeline.execution import (
    PIPELINE_SEQUENCE,
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
        del output_root
        return ExistingExperimentState.INCOMPLETE

    def delete(self, coordinate, output_root: Path) -> None:
        del output_root
        self.deleted.append(coordinate.stable_key)


class _SuccessfulRunner:
    def __init__(self) -> None:
        self.stages: list[PipelineStage] = []

    def run(self, stage: PipelineStage, coordinate) -> StageExecution:
        del coordinate
        self.stages.append(stage)
        return StageExecution(stage=stage, outcome=StageOutcome.COMPLETED, evidence="tiny deterministic fixture")


def test_campaign_resume_deletes_incomplete_cells_and_restarts_in_canonical_order(tmp_path: Path) -> None:
    declaration = next(item for item in EXPERIMENTS if item.id is ExperimentId.DITTO_ABSORPTION_STRESS_TEST)
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
    campaign = build_campaign(plan)
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
    assert tuple(runner.stages) == PIPELINE_SEQUENCE * len(campaign.entries)
