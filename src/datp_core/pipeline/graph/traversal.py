"""Deterministic topological traversal and relationship queries."""

from __future__ import annotations

import networkx as nx

from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.graph.validation import validate_acyclic
from datp_core.pipeline.stages.jobs import StageJob


class UnknownJobError(KeyError):
    """The requested graph node is not present in the graph."""


def lexicographical_topological_sort(graph: PlanningGraph) -> tuple[StageJob, ...]:
    validate_acyclic(graph)
    nx_graph = graph.graph
    sorted_nodes = list(nx.lexicographical_topological_sort(nx_graph, key=lambda n: n))
    jobs_by_key = {j.node_key: j for j in graph.jobs}
    return tuple(jobs_by_key[node] for node in sorted_nodes)


def topological_generations(graph: PlanningGraph) -> tuple[tuple[StageJob, ...], ...]:
    validate_acyclic(graph)
    nx_graph = graph.graph
    result: list[tuple[StageJob, ...]] = []
    jobs_by_key = {j.node_key: j for j in graph.jobs}
    for gen in nx.topological_generations(nx_graph):
        sorted_gen_nodes = sorted(gen, key=lambda n: n)
        gen_jobs = tuple(jobs_by_key[node] for node in sorted_gen_nodes)
        if gen_jobs:
            result.append(gen_jobs)
    return tuple(result)


def predecessors(graph: PlanningGraph, node_key: GraphNodeKey) -> tuple[GraphNodeKey, ...]:
    _require_job(graph, node_key)
    return graph.predecessors(node_key)


def successors(graph: PlanningGraph, node_key: GraphNodeKey) -> tuple[GraphNodeKey, ...]:
    _require_job(graph, node_key)
    return graph.successors(node_key)


def ancestors(graph: PlanningGraph, node_key: GraphNodeKey) -> tuple[GraphNodeKey, ...]:
    _require_job(graph, node_key)
    nx_graph = graph.graph
    return tuple(sorted(nx.ancestors(nx_graph, node_key), key=lambda n: n))


def descendants(graph: PlanningGraph, node_key: GraphNodeKey) -> tuple[GraphNodeKey, ...]:
    _require_job(graph, node_key)
    nx_graph = graph.graph
    return tuple(sorted(nx.descendants(nx_graph, node_key), key=lambda n: n))


def try_predecessors(graph: PlanningGraph, node_key: GraphNodeKey) -> tuple[GraphNodeKey, ...] | None:
    if not graph.has_job(node_key):
        return None
    return graph.predecessors(node_key)


def _require_job(graph: PlanningGraph, node_key: GraphNodeKey) -> None:
    if not graph.has_job(node_key):
        raise UnknownJobError(f"Unknown key '{node_key.label}' in graph query")
