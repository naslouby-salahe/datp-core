"""Planning graph: immutable DAG of stage jobs with structural validation."""

from __future__ import annotations

import networkx as nx

from datp_core.core.identifiers import JobId
from datp_core.pipeline.stages.jobs import StageJob


class DuplicateJobError(ValueError):
    """A JobId appears more than once in the graph."""


class MissingDependencyError(ValueError):
    """A job depends on a JobId not present in the graph."""


class DuplicateOutputArtifactError(ValueError):
    """Multiple jobs declare the same output artifact."""


class PlanningGraph:
    def __init__(self, jobs: tuple[StageJob, ...]) -> None:
        self._jobs: dict[JobId, StageJob] = {}
        for j in jobs:
            if j.job_id in self._jobs:
                raise DuplicateJobError(f"Duplicate JobId in planning graph: {j.job_id}")
            self._jobs[j.job_id] = j

        job_ids = set(self._jobs.keys())
        for j in jobs:
            for dep_id in j.dependencies:
                if dep_id not in job_ids:
                    raise MissingDependencyError(f"Job '{j.job_id}' depends on missing job '{dep_id}'")

        outputs: dict[str, JobId] = {}
        for j in jobs:
            output_name = j.output.artifact_id.value
            if output_name in outputs:
                raise DuplicateOutputArtifactError(
                    f"Jobs '{j.job_id}' and '{outputs[output_name]}' both declare output '{output_name}'"
                )
            outputs[output_name] = j.job_id

        self._graph = nx.DiGraph()
        for j in jobs:
            self._graph.add_node(j.job_id, job=j)
            for dep_id in j.dependencies:
                self._graph.add_edge(dep_id, j.job_id)

    @property
    def jobs(self) -> tuple[StageJob, ...]:
        return tuple(self._jobs.values())

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    def _has_job(self, job_id: JobId) -> bool:
        return job_id in self._graph
