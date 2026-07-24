"""Deterministic topological traversal and relationship queries."""

from __future__ import annotations

import networkx as nx

from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import StageNodeKey


class UnknownJobError(KeyError):
    """The requested StageNodeKey is not present in the graph."""


def lexicographical_topological_sort(graph: PlanningGraph) -> tuple[StageJob, ...]:
    validate_acyclic(graph)
    nx_graph = graph._graph  # noqa: SLF001
    sorted_nodes = list(nx.lexicographical_topological_sort(nx_graph, key=lambda n: n))
    jobs_by_key = {j.node_key: j for j in graph.jobs}
    return tuple(jobs_by_key[node] for node in sorted_nodes)


def topological_generations(graph: PlanningGraph) -> tuple[tuple[StageJob, ...], ...]:
    validate_acyclic(graph)
    nx_graph = graph._graph  # noqa: SLF001
    result: list[tuple[StageJob, ...]] = []
    jobs_by_key = {j.node_key: j for j in graph.jobs}
    for gen in nx.topological_generations(nx_graph):
        sorted_gen_nodes = sorted(gen, key=lambda n: n)
        gen_jobs = tuple(jobs_by_key[node] for node in sorted_gen_nodes)
        if gen_jobs:
            result.append(gen_jobs)
    return tuple(result)


def predecessors(graph: PlanningGraph, node_key: StageNodeKey) -> tuple[StageNodeKey, ...]:
    _require_job(graph, node_key)
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx_graph.predecessors(node_key), key=lambda n: n))


def successors(graph: PlanningGraph, node_key: StageNodeKey) -> tuple[StageNodeKey, ...]:
    _require_job(graph, node_key)
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx_graph.successors(node_key), key=lambda n: n))


def ancestors(graph: PlanningGraph, node_key: StageNodeKey) -> tuple[StageNodeKey, ...]:
    _require_job(graph, node_key)
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx.ancestors(nx_graph, node_key), key=lambda n: n))


def descendants(graph: PlanningGraph, node_key: StageNodeKey) -> tuple[StageNodeKey, ...]:
    _require_job(graph, node_key)
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx.descendants(nx_graph, node_key), key=lambda n: n))


def try_predecessors(graph: PlanningGraph, node_key: StageNodeKey) -> tuple[StageNodeKey, ...] | None:
    if not graph._has_job(node_key):  # noqa: SLF001
        return None
    nx_graph = graph._graph  # noqa: SLF001
    return tuple(sorted(nx_graph.predecessors(node_key), key=lambda n: n))


def _require_job(graph: PlanningGraph, node_key: StageNodeKey) -> None:
    if not graph._has_job(node_key):  # noqa: SLF001
        raise UnknownJobError(f"Unknown key '{node_key.label}' in graph query")
