"""Execution plan validation."""

from __future__ import annotations

from attrs import define

from datp_core.artifacts.identity import ArtifactKey, ArtifactKind
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.traversal import lexicographical_topological_sort
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.enums import StageKind
from datp_core.pipeline.stages.node_key import StageNodeKey


@define(frozen=True, slots=True, kw_only=True)
class PlanValidationResult:
    is_valid: bool
    errors: tuple[str, ...]
    job_count: int
    dependency_count: int


class ExecutionPlanValidator:
    @staticmethod
    def _build_producer_map(graph: PlanningGraph, errors: list[str]) -> dict[ArtifactKey, StageNodeKey]:
        producers: dict[ArtifactKey, StageNodeKey] = {}
        for job in graph.jobs:
            if job.output in producers:
                errors.append(f"Multiple producers found for artifact output '{job.output.node_key.label}'")
            producers[job.output] = job.node_key
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
    def _validate_job_inputs(
        graph: PlanningGraph, producers: dict[ArtifactKey, StageNodeKey], errors: list[str]
    ) -> None:
        for job in graph.jobs:
            for inp in job.inputs:
                if inp not in producers:
                    errors.append(
                        f"Job '{job.node_key.label}' consumes artifact '{inp.node_key.label}' "
                        "which has no producer in the plan"
                    )

            if job.stage is StageKind.THRESHOLD_CONSTRUCTION and any(
                item.kind is ArtifactKind.TEST_SCORES for item in job.inputs
            ):
                errors.append(f"Threshold job '{job.node_key.label}' must not consume test scores")
            if job.stage is StageKind.OPERATING_POINT_EVALUATION and any(
                item.kind in {ArtifactKind.CALIBRATION_SCORES, ArtifactKind.FUTURE_RECALIBRATION_SCORES}
                for item in job.inputs
            ):
                errors.append(f"Evaluation job '{job.node_key.label}' must not consume calibration scores")


def validate_planning_graph(graph: PlanningGraph) -> None:
    validator = ExecutionPlanValidator()
    res = validator.validate(graph)
    if not res.is_valid:
        raise ValueError(f"Planning graph validation failed: {res.errors}")
