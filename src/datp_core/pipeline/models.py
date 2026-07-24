"""Pipeline stage kinds, job identity/outcomes, and the pre-execution DAG planning graph."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import networkx as nx

from datp_core.artifacts.models import ArtifactKey
from datp_core.core.identifiers import ExperimentId, JobId, PopulationId, ThresholdPolicyId


class StageKind(Enum):
    PREFLIGHT = "preflight"
    DATASET_MATERIALIZATION = "dataset_materialization"
    MODEL_TRAINING = "model_training"
    CHECKPOINT_SELECTION = "checkpoint_selection"
    SCORE_GENERATION = "score_generation"
    CALIBRATION_SUBSAMPLING = "calibration_subsampling"
    THRESHOLD_CONSTRUCTION = "threshold_construction"
    OPERATING_POINT_EVALUATION = "operating_point_evaluation"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    REPORT_GENERATION = "report_generation"
    RESULT_FREEZE = "result_freeze"


class JobExecutionStatus(Enum):
    SUCCESS = "success"
    REUSED = "reused"
    SKIPPED = "skipped"
    SUPPRESSED = "suppressed"
    FAILED = "failed"
    INFEASIBLE = "infeasible"
    BLOCKED_BY_DEPENDENCY = "blocked_by_dependency"


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJobContext:
    """Immutable identity context carried by every DAG job.

    Handlers must read typed fields rather than parse job_id or artifact_id strings.
    """

    experiment_id: ExperimentId
    seed: int | None = None
    evaluation_label: str | None = None
    population_id: PopulationId | None = None
    recalibration_mode: str | None = None
    threshold_policy_id: ThresholdPolicyId | None = None
    dataset_setup_id: str | None = None
    materialization_id: str | None = None
    partition_condition: str | None = None
    federated_proximal_mu: float | None = None
    ditto_proximal_weight: float | None = None
    threshold_quantile: float | None = None
    shrinkage_weight: float | None = None
    federated_summary_fixed_k: float | None = None
    calibration_sample_count: int | None = None
    calibration_replicate: int | None = None
    fingerprint_features: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJob:
    job_id: JobId
    stage: StageKind
    context: StageJobContext
    inputs: tuple[ArtifactKey, ...]
    output: ArtifactKey
    dependencies: tuple[JobId, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class StageJobOutcome:
    job_id: JobId
    stage: StageKind
    status: JobExecutionStatus
    produced_artifact: ArtifactKey | None = None
    error_message: str | None = None

    @classmethod
    def succeeded(cls, *, job_id: JobId, stage: StageKind, produced_artifact: ArtifactKey) -> StageJobOutcome:
        if produced_artifact is None:
            raise ValueError("A succeeded outcome must have a produced artifact")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SUCCESS, produced_artifact=produced_artifact)

    @classmethod
    def reused(cls, *, job_id: JobId, stage: StageKind, produced_artifact: ArtifactKey) -> StageJobOutcome:
        if produced_artifact is None:
            raise ValueError("A reused outcome must have a produced artifact")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.REUSED, produced_artifact=produced_artifact)

    @classmethod
    def failed(cls, *, job_id: JobId, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("A failed outcome must carry an error message")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.FAILED, error_message=error_message)

    @classmethod
    def skipped(cls, *, job_id: JobId, stage: StageKind, error_message: str | None = None) -> StageJobOutcome:
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SKIPPED, error_message=error_message)

    @classmethod
    def suppressed(cls, *, job_id: JobId, stage: StageKind, error_message: str | None = None) -> StageJobOutcome:
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.SUPPRESSED, error_message=error_message)

    @classmethod
    def infeasible(cls, *, job_id: JobId, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("An infeasible outcome must carry an error message")
        return cls(job_id=job_id, stage=stage, status=JobExecutionStatus.INFEASIBLE, error_message=error_message)

    @classmethod
    def blocked_by_dependency(cls, *, job_id: JobId, stage: StageKind, error_message: str) -> StageJobOutcome:
        if not error_message:
            raise ValueError("A blocked-by-dependency outcome must carry an error message")
        return cls(
            job_id=job_id, stage=stage, status=JobExecutionStatus.BLOCKED_BY_DEPENDENCY, error_message=error_message
        )


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
            sorted_gen_nodes = sorted(gen, key=lambda n: n.value)
            gen_jobs = tuple(self._jobs[node] for node in sorted_gen_nodes)
            if gen_jobs:
                res.append(gen_jobs)
        return tuple(res)

    def predecessors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id not in self._graph:
            return ()
        return tuple(sorted(self._graph.predecessors(job_id), key=lambda n: n.value))

    def successors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id not in self._graph:
            return ()
        return tuple(sorted(self._graph.successors(job_id), key=lambda n: n.value))

    def ancestors(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id not in self._graph:
            return ()
        return tuple(sorted(nx.ancestors(self._graph, job_id), key=lambda n: n.value))

    def descendants(self, job_id: JobId) -> tuple[JobId, ...]:
        if job_id not in self._graph:
            return ()
        return tuple(sorted(nx.descendants(self._graph, job_id), key=lambda n: n.value))

    @property
    def node_count(self) -> int:
        return self._graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self._graph.number_of_edges()

    @property
    def jobs(self) -> tuple[StageJob, ...]:
        return tuple(self._jobs.values())
