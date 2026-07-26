"""Dagster definitions — thin orchestration wrapper.

Every execution path delegates to the existing pipeline.
Dagster provides scheduling, observability, and the canonical run graph.
"""

from __future__ import annotations

import dagster as dg

from datp_core.pipeline.stages.enums import StageKind

STAGE_ORDER: tuple[StageKind, ...] = (
    StageKind.PREFLIGHT,
    StageKind.DATASET_MATERIALIZATION,
    StageKind.MODEL_TRAINING,
    StageKind.CHECKPOINT_SELECTION,
    StageKind.SCORE_GENERATION,
    StageKind.CALIBRATION_SUBSAMPLING,
    StageKind.THRESHOLD_CONSTRUCTION,
    StageKind.OPERATING_POINT_EVALUATION,
    StageKind.STATISTICAL_ANALYSIS,
    StageKind.RESULT_FREEZE,
    StageKind.REPORT_GENERATION,
)


def _make_experiment_job(experiment_id: str) -> dg.JobDefinition:
    """Create a Dagster job that delegates to the canonical experiment pipeline."""

    @dg.op(name=f"{experiment_id}_execute")
    def _run_experiment(context) -> None:
        import os

        os.environ.setdefault("DATP_REPOSITORY_ROOT", "/home/naslouby/Projects/datp-core")
        os.environ.setdefault("DATP_EXECUTION_PROFILE", "scientific")

        from datp_core.app import build_application
        from datp_core.core.identifiers import ExperimentId

        app = build_application()
        result = app.run_experiment.run(ExperimentId(experiment_id), override=False)
        if not result.success:
            raise RuntimeError(f"Experiment {experiment_id} failed: {result.error_message}")

    @dg.graph(name=f"experiment_{experiment_id}")
    def _experiment_graph() -> None:
        _run_experiment()

    return _experiment_graph.to_job(name=f"datp_{experiment_id}")


def build_dagster_definitions(experiment_ids: tuple[str, ...]) -> dg.Definitions:
    """Build Dagster Definitions for all configured experiments."""
    jobs = [_make_experiment_job(exp_id) for exp_id in experiment_ids]
    return dg.Definitions(jobs=jobs)
