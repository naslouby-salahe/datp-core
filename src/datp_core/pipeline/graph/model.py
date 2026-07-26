"""Planning graph: immutable DAG of stage jobs with structural validation."""

from __future__ import annotations

import networkx as nx

from datp_core.pipeline.graph.key import GraphNodeKey
from datp_core.pipeline.stages.jobs import StageJob


class DuplicateJobError(ValueError):
    """A graph-private key appears more than once in the graph."""


class MissingDependencyError(ValueError):
    """A job depends on a graph-private key not present in the graph."""


class DuplicateOutputPathError(ValueError):
    """Multiple jobs declare the same semantic output path."""


class PlanningGraph:
    def __init__(self, jobs: tuple[StageJob, ...]) -> None:
        self._jobs: dict[GraphNodeKey, StageJob] = {}
        for j in jobs:
            if j.node_key in self._jobs:
                raise DuplicateJobError(f"Duplicate graph node key: {j.node_key.label}")
            self._jobs[j.node_key] = j

        job_ids = set(self._jobs.keys())
        for j in jobs:
            for dep_id in j.dependencies:
                if dep_id not in job_ids:
                    raise MissingDependencyError(f"Job '{j.node_key.label}' depends on missing key '{dep_id.label}'")

        outputs: dict[str, StageJob] = {}
        for j in jobs:
            for output in j.outputs:
                if output.relative_path in outputs:
                    other = outputs[output.relative_path]
                    raise DuplicateOutputPathError(
                        f"Jobs '{j.node_key.label}' and '{other.node_key.label}' both declare output "
                        f"'{output.relative_path}'"
                    )
                outputs[output.relative_path] = j

        self._graph = nx.DiGraph()
        for j in jobs:
            self._graph.add_node(j.node_key, job=j)
            for dep_id in j.dependencies:
                self._graph.add_edge(dep_id, j.node_key)

    @property
    def jobs(self) -> tuple[StageJob, ...]:
        return tuple(self._jobs.values())

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def has_job(self, node_key: GraphNodeKey) -> bool:
        return node_key in self._graph

    @property
    def graph(self) -> nx.DiGraph:
        return self._graph

    @property
    def nodes(self) -> tuple[GraphNodeKey, ...]:
        return tuple(sorted(self._graph.nodes()))

    @property
    def edges(self) -> tuple[tuple[GraphNodeKey, GraphNodeKey], ...]:
        return tuple(self._graph.edges())

    def successors(self, node_key: GraphNodeKey) -> tuple[GraphNodeKey, ...]:
        return tuple(sorted(self._graph.successors(node_key)))

    def predecessors(self, node_key: GraphNodeKey) -> tuple[GraphNodeKey, ...]:
        return tuple(sorted(self._graph.predecessors(node_key)))
