"""Execution plan validation."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.traversal import lexicographical_topological_sort
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.enums import StageKind


class PlanValidationResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    is_valid: bool
    errors: tuple[str, ...]
    job_count: int
    dependency_count: int


class ExecutionPlanValidator:
    @staticmethod
    def _build_producer_map(graph: PlanningGraph, errors: list[str]) -> dict[str, GraphNodeKey]:
        producers: dict[str, GraphNodeKey] = {}
        for job in graph.jobs:
            for output in job.outputs:
                if output.relative_path in producers:
                    errors.append(f"Multiple producers found for output '{output.relative_path}'")
                producers[output.relative_path] = job.node_key
        return producers

    def validate(self, graph: PlanningGraph) -> PlanValidationResult:
        errors: list[str] = []

        if graph.node_count == 0:
            errors.append("Planning graph contains no job nodes")
            return PlanValidationResult(
                is_valid=False,
                errors=tuple(errors),
                job_count=0,
                dependency_count=0,
            )

        try:
            validate_acyclic(graph)
        except ValueError as exc:
            errors.append(str(exc))

        top_order = lexicographical_topological_sort(graph)
        if len(top_order) != graph.node_count:
            errors.append("Topological sort node count mismatch")

        producers = self._build_producer_map(graph, errors)
        self._validate_job_inputs(graph, producers, errors)

        is_valid = len(errors) == 0
        return PlanValidationResult(
            is_valid=is_valid,
            errors=tuple(errors),
            job_count=graph.node_count,
            dependency_count=graph.edge_count,
        )

    @staticmethod
    def _validate_job_inputs(graph: PlanningGraph, producers: dict[str, GraphNodeKey], errors: list[str]) -> None:
        for job in graph.jobs:
            for inp in job.inputs:
                if inp.relative_path not in producers:
                    errors.append(
                        f"Job '{job.node_key.label}' consumes input '{inp.relative_path}' "
                        "which has no producer in the plan"
                    )
                elif producers[inp.relative_path] != inp.producer:
                    errors.append(
                        f"Job '{job.node_key.label}' input '{inp.name}' declares the wrong producer for "
                        f"'{inp.relative_path}'"
                    )

            input_names = {item.name for item in job.inputs}
            if job.stage is StageKind.THRESHOLD_CONSTRUCTION and "test_scores" in input_names:
                errors.append(f"Threshold job '{job.node_key.label}' must not consume test scores")
            if job.stage is StageKind.OPERATING_POINT_EVALUATION and input_names & {
                "calibration_scores",
                "future_recalibration_scores",
                "calibration_subset_scores",
            }:
                errors.append(f"Evaluation job '{job.node_key.label}' must not consume calibration scores")


def validate_planning_graph(graph: PlanningGraph) -> None:
    validator = ExecutionPlanValidator()
    res = validator.validate(graph)
    if not res.is_valid:
        raise ValueError(f"Planning graph validation failed: {res.errors}")
