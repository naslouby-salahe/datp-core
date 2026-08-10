from dataclasses import replace
from pathlib import Path

import pytest

from datp_core.app.planning import PlanDisposition, PlanningEvidence, PlanReason, expand_experiment_plan
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ExperimentId, FederatedThresholdMethod
from datp_core.core.numeric import Seed
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution import engine, execute_declared_experiment_seed
from datp_core.experiments.registry import EXPERIMENTS


def _declaration(experiment_id: ExperimentId):
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    assert len(matches) == 1
    return matches[0]


def test_execute_declared_experiment_seed_raises_on_empty_campaign(tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.DITTO_ABSORPTION_STRESS_TEST)
    with pytest.raises(ScientificContractError):
        execute_declared_experiment_seed(
            declaration=declaration,
            seed_cohort=SeedCohort(values=(Seed(0),)),
            reason=PlanReason("fixture"),
            output_root=tmp_path,
            overwrite=False,
        )


def test_pipeline_runner_shares_fixed_detector_evidence_only_within_one_campaign(monkeypatch, tmp_path: Path) -> None:
    declaration = _declaration(ExperimentId.SHARED_VS_LOCAL_CONFIRMATION)
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=SeedCohort(values=(Seed(0),)),
        evidence=(
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.EXECUTABLE,
                reason=PlanReason("fixture"),
            ),
        ),
    )
    first_coordinate = plan.executable[0].coordinate
    alternate_method = next(
        method
        for method in (FederatedThresholdMethod.SHARED_THRESHOLD, FederatedThresholdMethod.LOCAL_THRESHOLD)
        if method is not first_coordinate.threshold_method
    )
    second_coordinate = replace(first_coordinate, threshold_method=alternate_method)

    class Workspace:
        def __init__(self, **kwargs: object) -> None:
            self.coordinate = kwargs["coordinate"]
            self.output_root = kwargs["output_root"]
            self.context = object()
            self.training = object()
            self.scores = object()
            self.fixed_context = kwargs.get("fixed_context")
            self.fixed_training = kwargs.get("fixed_training")
            self.fixed_scores = kwargs.get("fixed_scores")

    monkeypatch.setattr(engine, "ExperimentWorkspace", Workspace)
    runner = engine.PipelineStageRunner()

    first = runner._workspace_for(first_coordinate, tmp_path)
    second = runner._workspace_for(second_coordinate, tmp_path)

    assert second.fixed_context is first.context
    assert second.fixed_training is first.training
    assert second.fixed_scores is first.scores
