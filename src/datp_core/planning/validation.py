"""Validation checks for planning graphs."""

from __future__ import annotations

from datp_core.planning.graph import PlanningGraph


def validate_planning_graph(graph: PlanningGraph) -> None:
    graph.validate_acyclic()
    if graph.node_count == 0:
        raise ValueError("Planning graph contains no job nodes")
    top_order = graph.lexicographical_topological_sort()
    if len(top_order) != graph.node_count:
        raise ValueError("Topological sort length mismatch")
