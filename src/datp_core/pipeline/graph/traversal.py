"""Deterministic topological traversal and relationship queries."""

from __future__ import annotations

import networkx as nx

from datp_core.core.identifiers import JobId
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.jobs import StageJob


class UnknownJobError(KeyError):
    """The requested JobId is not present in the graph."""


def lexicographical_topological_sort(graph: PlanningGraph) -> tuple[StageJob, ...]:
    validate_acyclic(graph)
    nx_graph = graph._graph  # noqa: SLF001
    sorted_nodes = list(nx.lexicographical_topological_sort(nx_graph, key=lambda n: n.value))
    jobs_by_id = {j.job_id: j for j in graph.jobs}
    return tuple(jobs_by_id[node] for node in sorted_nodes)


def topological_generations(graph: PlanningGraph) -> tuple[tuple[StageJob, ...], ...]:
    validate_acyclic(graph)
    nx_graph = graph._graph  # noqa: SLF001
    result: list[tuple[StageJob, ...]] = []
    jobs_by_id = {j.job_id: j for j in graph.jobs}
    for gen in nx.topological_generations(nx_graph):
        sorted_gen_nodes = sorted(gen, key=lambda n: n.value)
        gen_jobs = tuple(jobs_by_id[node] for node in sorted_gen_nodes)
        if gen_jobs:
            result.append(gen_jobs)
    return tuple(result)


def predecessors(graph: PlanningGraph, job_id: JobId) -> tuple[JobId, ...]:
    _require_job(graph, job_id)
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx_graph.predecessors(job_id), key=lambda n: n.value))


def successors(graph: PlanningGraph, job_id: JobId) -> tuple[JobId, ...]:
    _require_job(graph, job_id)
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx_graph.successors(job_id), key=lambda n: n.value))


def ancestors(graph: PlanningGraph, job_id: JobId) -> tuple[JobId, ...]:
    _require_job(graph, job_id)
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx.ancestors(nx_graph, job_id), key=lambda n: n.value))


def descendants(graph: PlanningGraph, job_id: JobId) -> tuple[JobId, ...]:
    _require_job(graph, job_id)
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx.descendants(nx_graph, job_id), key=lambda n: n.value))


def try_predecessors(graph: PlanningGraph, job_id: JobId) -> tuple[JobId, ...] | None:
    if not graph._has_job(job_id):  # noqa: SLF001
        return None
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx_graph.predecessors(job_id), key=lambda n: n.value))


def _require_job(graph: PlanningGraph, job_id: JobId) -> None:
    if not graph._has_job(job_id):  # noqa: SLF001
        raise UnknownJobError(f"Unknown job '{job_id.value}' in graph query")
