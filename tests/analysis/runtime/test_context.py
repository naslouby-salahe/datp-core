"""Unit tests for AnalysisExecutionContext."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from datp_core.analysis.errors import InvalidAnalysisConfigurationError
from datp_core.analysis.runtime.context import AnalysisExecutionContext
from datp_core.core.identifiers import EvaluationLabel, ExperimentId, PopulationId, ThresholdPolicyId
from datp_core.core.seeding import Seed
from datp_core.experiments import EvaluationSpecRecord, ExperimentRecord
from datp_core.experiments.catalogue.evaluations import RunRequirement


@pytest.fixture
def dummy_experiment() -> ExperimentRecord:
    eval_spec = EvaluationSpecRecord(
        label="eval_main",
        population_id=PopulationId("pop_1"),
        recalibration_mode="frozen",  # type: ignore[arg-type]
        threshold_policy_id=ThresholdPolicyId("pol_1"),
        run_requirement=RunRequirement.MANDATORY,
        overrides=None,
    )
    exp = MagicMock(spec=ExperimentRecord)
    exp.identifier = ExperimentId("exp_1")
    exp.display_name = "Experiment 1"
    exp.evaluations = (eval_spec,)
    exp.population_ids = (PopulationId("pop_1"),)
    return exp


def test_context_evaluation_lookup(dummy_experiment: ExperimentRecord) -> None:
    ctx = AnalysisExecutionContext.model_construct(
        config=MagicMock(),
        artifacts=MagicMock(),
        experiment=dummy_experiment,
        seeds=(Seed(1), Seed(2)),
        statistical_analysis=MagicMock(),
    )
    spec = ctx.evaluation(EvaluationLabel("eval_main"))
    assert spec.label == "eval_main"

    with pytest.raises(InvalidAnalysisConfigurationError):
        ctx.evaluation(EvaluationLabel("non_existent"))


def test_context_stage_job_context_factories(dummy_experiment: ExperimentRecord) -> None:
    ctx = AnalysisExecutionContext.model_construct(
        config=MagicMock(),
        artifacts=MagicMock(),
        experiment=dummy_experiment,
        seeds=(Seed(1), Seed(2)),
        statistical_analysis=MagicMock(),
    )
    eval_job_ctx = ctx.evaluation_context(EvaluationLabel("eval_main"), Seed(1))
    assert eval_job_ctx.experiment_id == ExperimentId("exp_1")
    assert eval_job_ctx.seed == 1
    assert eval_job_ctx.evaluation_label == "eval_main"
    assert eval_job_ctx.population_id == PopulationId("pop_1")

    score_job_ctx = ctx.score_context(EvaluationLabel("eval_main"), Seed(2))
    assert score_job_ctx.seed == 2

    model_job_ctx = ctx.model_context(Seed(1))
    assert model_job_ctx.seed == 1
    assert model_job_ctx.population_id == PopulationId("pop_1")

    sel_job_ctx = ctx.selection_context(Seed(1))
    assert sel_job_ctx.seed == 1
