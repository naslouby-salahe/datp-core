"""Validation checks and ExecutionPlanValidator for planning graphs."""

from __future__ import annotations

from attrs import define

from datp_core.domain.artifacts import ArtifactKey, ArtifactKind
from datp_core.domain.identifiers import JobId
from datp_core.planning.graph import PlanningGraph


@define(frozen=True, slots=True, kw_only=True)
class PlanValidationResult:
    is_valid: bool
    errors: tuple[str, ...]
    job_count: int
    dependency_count: int


class ExecutionPlanValidator:
    """Validator performing deep structural and artifact contract checks on planning graphs."""

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

        # Check acyclicity
        try:
            graph.validate_acyclic()
        except ValueError as exc:
            errors.append(str(exc))

        # Check job node count vs topological sort
        top_order = graph.lexicographical_topological_sort()
        if len(top_order) != graph.node_count:
            errors.append("Topological sort node count mismatch")

        # Map outputs to producer job IDs
        producers: dict[ArtifactKey, JobId] = {}
        for job in graph.jobs:
            if job.output in producers:
                errors.append(f"Multiple producers found for artifact output '{job.output.artifact_id}'")
            producers[job.output] = job.job_id

        # Validate input artifact producer existence
        for job in graph.jobs:
            for inp in job.inputs:
                if inp not in producers:
                    errors.append(
                        f"Job '{job.job_id}' consumes artifact '{inp.artifact_id}' which has no producer in the plan"
                    )

            if job.stage.value == "threshold_construction" and any(
                item.kind is ArtifactKind.TEST_SCORES for item in job.inputs
            ):
                errors.append(f"Threshold job '{job.job_id}' must not consume test scores")
            if job.stage.value == "operating_point_evaluation" and any(
                item.kind is ArtifactKind.CALIBRATION_SCORES for item in job.inputs
            ):
                errors.append(f"Evaluation job '{job.job_id}' must not consume calibration scores")

        is_valid = len(errors) == 0
        return PlanValidationResult(
            is_valid=is_valid,
            errors=tuple(errors),
            job_count=graph.node_count,
            dependency_count=graph.edge_count,
        )


def validate_planning_graph(graph: PlanningGraph) -> None:
    validator = ExecutionPlanValidator()
    res = validator.validate(graph)
    if not res.is_valid:
        raise ValueError(f"Planning graph validation failed: {res.errors}")
