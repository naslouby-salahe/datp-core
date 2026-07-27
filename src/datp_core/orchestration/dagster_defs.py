"""Dagster definitions — thin orchestration wrapper.

Each experiment expands to a DAG of stage-level Dagster ops generated from the
planning graph of StageJob objects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import dagster as dg

from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.planning.compilation import compile_experiment
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.traversal import lexicographical_topological_sort
from datp_core.pipeline.stages.enums import JobExecutionStatus
from datp_core.pipeline.stages.jobs import StageJob

if TYPE_CHECKING:
    from datp_core.app import DatpApplication


def _safe_label(raw: str) -> str:
    return raw.replace("-", "_").replace(" ", "_").replace(".", "_")


def _find_job(graph: PlanningGraph, node_key: object) -> StageJob | None:
    for job in graph.jobs:
        if job.node_key == node_key:
            return job
    return None


def _make_job_op(experiment_id: str, job: StageJob, app: DatpApplication) -> dg.OpDefinition:
    safe_label = _safe_label(job.node_key.label)
    op_name = f"{experiment_id}_{safe_label}"
    stage = job.stage

    @dg.op(name=op_name)
    def _execute(context) -> None:
        compiled = compile_experiment(app.config, ExperimentId(experiment_id))
        builder = app.plan_builder
        graph = builder.build(compiled)
        target = _find_job(graph, job.node_key)
        if target is None:
            context.log.info(
                "Job %s not found for experiment %s, skipping",
                job.node_key.label,
                experiment_id,
            )
            return
        handler = app.execute_experiment.handler_registry.get(stage)
        outcome = handler.execute(target)
        if outcome.status is not JobExecutionStatus.SUCCESS:
            raise RuntimeError(
                f"Job '{job.node_key.label}' for experiment '{experiment_id}' failed: {outcome.error_message}"
            )

    return _execute


def _make_experiment_job(experiment_id: str, app: DatpApplication) -> dg.JobDefinition:
    compiled = compile_experiment(app.config, ExperimentId(experiment_id))
    graph = app.plan_builder.build(compiled)
    sorted_jobs = lexicographical_topological_sort(graph)

    op_defs = {job.node_key: _make_job_op(experiment_id, job, app) for job in sorted_jobs}

    @dg.graph(name=f"experiment_{experiment_id}")
    def _experiment_graph() -> None:
        outputs: dict = {}
        for job in sorted_jobs:
            dependency_outputs = tuple(outputs[d] for d in job.dependencies)
            if dependency_outputs:
                outputs[job.node_key] = op_defs[job.node_key](*dependency_outputs)
            else:
                outputs[job.node_key] = op_defs[job.node_key]()

    return _experiment_graph.to_job(name=f"datp_{experiment_id}")


def build_dagster_definitions(app: DatpApplication) -> dg.Definitions:
    exp_ids = tuple(eid.value for eid in app.config.experiments)
    jobs = [_make_experiment_job(exp_id, app) for exp_id in exp_ids]
    return dg.Definitions(jobs=jobs)
