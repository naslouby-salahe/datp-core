"""Planning graph: immutable DAG of stage jobs with structural validation."""

from __future__ import annotations

import networkx as nx

from datp_core.pipeline.stages.jobs import StageJob
from datp_core.pipeline.stages.node_key import StageNodeKey


class DuplicateJobError(ValueError):
    """A StageNodeKey appears more than once in the graph."""


class MissingDependencyError(ValueError):
    """A job depends on a StageNodeKey not present in the graph."""


class DuplicateOutputArtifactError(ValueError):
    """Multiple jobs declare the same output artifact."""


class PlanningGraph:
    def __init__(self, jobs: tuple[StageJob, ...]) -> None:
        self._jobs: dict[StageNodeKey, StageJob] = {}
        for j in jobs:
            if j.node_key in self._jobs:
                raise DuplicateJobError(f"Duplicate StageNodeKey in planning graph: {j.node_key.label}")
            self._jobs[j.node_key] = j

        job_ids = set(self._jobs.keys())
        for j in jobs:
            for dep_id in j.dependencies:
                if dep_id not in job_ids:
                    raise MissingDependencyError(
                        f"Job '{j.node_key.label}' depends on missing key '{dep_id.label}'"
                    )

        outputs: dict[StageNodeKey, StageJob] = {}
        for j in jobs:
            if j.output.node_key in outputs:
                other = outputs[j.output.node_key]
                raise DuplicateOutputArtifactError(
                    f"Jobs '{j.node_key.label}' and '{other.node_key.label}' both declare output "
                    f"'{j.output.node_key.label}'"
                )
            outputs[j.output.node_key] = j

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

    def _has_job(self, node_key: StageNodeKey) -> bool:
        return node_key in self._graph
