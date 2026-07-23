"""Pure pre-execution job DAG planning graph backed by NetworkX."""

from __future__ import annotations

import networkx as nx

from datp_core.domain.identifiers import JobId
from datp_core.domain.outcomes import StageJob


class PlanningGraph:
    """NetworkX wrapper for pre-execution DAG validation and topological analysis."""

    def __init__(self, jobs: tuple[StageJob, ...]) -> None:
        self._jobs: dict[JobId, StageJob] = {}
        for j in jobs:
            if j.job_id in self._jobs:
                raise ValueError(f"Duplicate JobId in planning graph: {j.job_id}")
            self._jobs[j.job_id] = j

        job_ids = set(self._jobs.keys())
        for j in jobs:
            for dep_id in j.dependencies:
                if dep_id not in job_ids:
                    raise ValueError(f"Job '{j.job_id}' depends on missing job '{dep_id}'")

        self._graph = nx.DiGraph()

        # Add nodes as JobId objects
        for j in jobs:
            self._graph.add_node(j.job_id, job=j)
            for dep_id in j.dependencies:
                self._graph.add_edge(dep_id, j.job_id)

    def validate_acyclic(self) -> None:
        if not nx.is_directed_acyclic_graph(self._graph):
            cycles = list(nx.simple_cycles(self._graph))
            raise ValueError(f"Job graph contains cycles: {cycles}")

    def lexicographical_topological_sort(self) -> tuple[StageJob, ...]:
        self.validate_acyclic()
        sorted_nodes = list(nx.lexicographical_topological_sort(self._graph, key=lambda n: n.value))
        return tuple(self._jobs[node] for node in sorted_nodes)

    def topological_generations(self) -> tuple[tuple[StageJob, ...], ...]:
        self.validate_acyclic()
        generations = list(nx.topological_generations(self._graph))
        res = []
        for gen in generations:
            sorted_gen_nodes = sorted(list(gen), key=lambda n: n.value)
            gen_jobs = tuple(self._jobs[node] for node in sorted_gen_nodes)
            if gen_jobs:
                res.append(gen_jobs)
        return tuple(res)

    def predecessors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id not in self._graph:
            return ()
        preds = list(self._graph.predecessors(job_id))
        return tuple(sorted(preds, key=lambda n: n.value))

    def successors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id not in self._graph:
            return ()
        succs = list(self._graph.successors(job_id))
        return tuple(sorted(succs, key=lambda n: n.value))

    def ancestors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id not in self._graph:
            return ()
        ancs = list(nx.ancestors(self._graph, job_id))
        return tuple(sorted(ancs, key=lambda n: n.value))

    def descendants(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id not in self._graph:
            return ()
        descs = list(nx.descendants(self._graph, job_id))
        return tuple(sorted(descs, key=lambda n: n.value))

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    @property
    def jobs(self) -> tuple[StageJob, ...]:
        return tuple(self._jobs.values())
