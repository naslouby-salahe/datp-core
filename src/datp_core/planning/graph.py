"""Pure pre-execution job DAG planning graph backed by NetworkX."""

from __future__ import annotations

import networkx as nx

from datp_core.domain.identifiers import JobId
from datp_core.domain.outcomes import StageJob


class PlanningGraph:
    """NetworkX wrapper for pre-execution DAG validation and topological analysis."""

    def __init__(self, jobs: tuple[StageJob, ...]) -> None:
        self._jobs: dict[JobId, StageJob] = {j.job_id: j for j in jobs}
        self._graph = nx.DiGraph()

        for j in jobs:
            self._graph.add_node(j.job_id.value, job=j)
            for dep_id in j.dependencies:
                if dep_id.value not in self._graph:
                    self._graph.add_node(dep_id.value)
                self._graph.add_edge(dep_id.value, j.job_id.value)

    def validate_acyclic(self) -> None:
        if not nx.is_directed_acyclic_graph(self._graph):
            cycles = list(nx.simple_cycles(self._graph))
            raise ValueError(f"Job graph contains cycles: {cycles}")

    def lexicographical_topological_sort(self) -> tuple[StageJob, ...]:
        self.validate_acyclic()
        sorted_nodes = [str(node_id) for node_id in nx.lexicographical_topological_sort(self._graph)]
        return tuple(self._jobs[JobId(value=node_id)] for node_id in sorted_nodes if JobId(value=node_id) in self._jobs)

    def topological_generations(self) -> tuple[tuple[StageJob, ...], ...]:
        self.validate_acyclic()
        generations = list(nx.topological_generations(self._graph))
        res = []
        for gen in generations:
            gen_nodes = [str(node) for node in gen]
            gen_jobs = tuple(self._jobs[JobId(value=node)] for node in gen_nodes if JobId(value=node) in self._jobs)
            if gen_jobs:
                res.append(gen_jobs)
        return tuple(res)

    def predecessors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id.value not in self._graph:
            return ()
        preds = [str(p) for p in self._graph.predecessors(job_id.value)]
        return tuple(JobId(value=p) for p in sorted(preds))

    def successors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id.value not in self._graph:
            return ()
        succs = [str(s) for s in self._graph.successors(job_id.value)]
        return tuple(JobId(value=s) for s in sorted(succs))

    def ancestors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id.value not in self._graph:
            return ()
        ancs = [str(a) for a in nx.ancestors(self._graph, job_id.value)]
        return tuple(JobId(value=a) for a in sorted(ancs))

    def descendants(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id.value not in self._graph:
            return ()
        descs = [str(d) for d in nx.descendants(self._graph, job_id.value)]
        return tuple(JobId(value=d) for d in sorted(descs))

    def transitive_reduction(self) -> PlanningGraph:
        tr_graph = nx.transitive_reduction(self._graph)
        new_jobs = []
        for j in self._jobs.values():
            preds = [str(p) for p in tr_graph.predecessors(j.job_id.value)]
            direct_preds = tuple(JobId(value=p) for p in sorted(preds))
            new_jobs.append(
                StageJob(
                    job_id=j.job_id,
                    stage=j.stage,
                    inputs=j.inputs,
                    output=j.output,
                    dependencies=direct_preds,
                )
            )
        return PlanningGraph(tuple(new_jobs))

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()
