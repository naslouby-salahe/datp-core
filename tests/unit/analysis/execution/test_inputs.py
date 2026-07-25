"""Exact typed-coordinate lookup coverage for statistical-analysis inputs."""

from __future__ import annotations

import pytest

from datp_core.analysis.execution.inputs import AnalysisInputBundle
from datp_core.core.identifiers import ExperimentId
from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.stages.context import StageJobContext
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.jobs import AnalysisInputCoordinates, StageInput


def _input(*, seed: int, evaluation_label: str, path: str) -> StageInput:
    context = StageJobContext(
        experiment_id=ExperimentId("analysis-input-test"), seed=seed, evaluation_label=evaluation_label
    )
    return StageInput(
        name=f"metrics-{seed}-{evaluation_label}",
        relative_path=path,
        producer=GraphNodeKey(label=f"evaluation-{seed}-{evaluation_label}"),
        coordinates=AnalysisInputCoordinates(
            producer_stage=StageKind.OPERATING_POINT_EVALUATION,
            output_name="client_metrics",
            context=context,
        ),
    )


def test_exact_coordinates_cannot_confuse_seed_one_with_seed_ten_or_overlapping_labels() -> None:
    bundle = AnalysisInputBundle.from_stage_inputs(
        (
            _input(seed=1, evaluation_label="baseline", path="metrics/seed-1-baseline.parquet"),
            _input(seed=10, evaluation_label="baseline", path="metrics/seed-10-baseline.parquet"),
            _input(seed=1, evaluation_label="baseline_extended", path="metrics/seed-1-baseline-extended.parquet"),
        )
    )

    seed_one = StageJobContext(experiment_id=ExperimentId("analysis-input-test"), seed=1, evaluation_label="baseline")
    seed_ten = StageJobContext(experiment_id=ExperimentId("analysis-input-test"), seed=10, evaluation_label="baseline")
    extended = StageJobContext(
        experiment_id=ExperimentId("analysis-input-test"), seed=1, evaluation_label="baseline_extended"
    )

    assert bundle.evaluation_metrics(seed_one) == "metrics/seed-1-baseline.parquet"
    assert bundle.evaluation_metrics(seed_ten) == "metrics/seed-10-baseline.parquet"
    assert bundle.evaluation_metrics(extended) == "metrics/seed-1-baseline-extended.parquet"


def test_missing_exact_coordinate_reports_the_requested_stage_output_and_context() -> None:
    bundle = AnalysisInputBundle.from_stage_inputs(
        (_input(seed=1, evaluation_label="baseline", path="metrics/seed-1-baseline.parquet"),)
    )
    missing = StageJobContext(experiment_id=ExperimentId("analysis-input-test"), seed=10, evaluation_label="baseline")

    with pytest.raises(ValueError, match="Analysis input is not declared: stage=operating_point_evaluation"):
        bundle.evaluation_metrics(missing)


def test_duplicate_exact_coordinates_are_rejected() -> None:
    first = _input(seed=1, evaluation_label="baseline", path="metrics/first.parquet")
    duplicate = _input(seed=1, evaluation_label="baseline", path="metrics/second.parquet")

    with pytest.raises(ValueError, match="duplicate artifact coordinates"):
        AnalysisInputBundle.from_stage_inputs((first, duplicate))
