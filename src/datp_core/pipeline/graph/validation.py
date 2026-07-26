"""Generic DAG validation: acyclicity and structural integrity."""

from __future__ import annotations

import networkx as nx

from datp_core.pipeline.graph.model import PlanningGraph


class PlanningCycleError(ValueError):
    def __init__(self, cycles: list[list[str]]) -> None:
        formatted = "; ".join(" → ".join(cycle) for cycle in cycles)
        super().__init__(f"Job graph contains cycles: {formatted}")
        self.cycles = cycles


def validate_acyclic(graph: PlanningGraph) -> None:
    nx_graph = graph.graph
    if not nx.is_directed_acyclic_graph(nx_graph):
        cycles = [[node.label for node in cycle] for cycle in nx.simple_cycles(nx_graph)]
        raise PlanningCycleError(cycles)
