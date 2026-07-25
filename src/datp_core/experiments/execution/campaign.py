"""Sequential campaign orchestration over validated experiment output folders."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import networkx as nx

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.catalogue.models import EvidenceRole, ExperimentRecord
from datp_core.experiments.execution.output_manager import ExperimentOutputManager, OutputState
from datp_core.experiments.execution.report import ExperimentExecutionReport
from datp_core.experiments.execution.use_case import ExperimentLifecycleUseCase, ExperimentRunStatus
from datp_core.experiments.planning import expand_campaign_jobs
from datp_core.experiments.planning.validation import validate_planning_graph
from datp_core.pipeline.graph.model import PlanningGraph


class CampaignExperimentStatus(Enum):
    SKIPPED_EXISTING = "skipped_existing"
    INCOMPLETE_RESTARTED = "incomplete_restarted"
    BLOCKED_PREREQUISITE = "blocked_prerequisite"
    BLOCKED_ANCHOR = "blocked_anchor"
    EXECUTED = "executed"
    INCOMPATIBLE = "incompatible"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class CampaignExperimentResult:
    experiment_id: ExperimentId
    status: CampaignExperimentStatus
    report: ExperimentExecutionReport | None = None
    error_message: str | None = None


@dataclass(frozen=True, slots=True)
class CampaignReport:
    results: tuple[CampaignExperimentResult, ...]
    total_experiments: int
    completed_or_skipped: int
    executed: int
    blocked: int
    failed: int
    success: bool

    @property
    def exit_code(self) -> int:
        return 0 if self.success else 1


def _build_experiment_dag(config: ResolvedProjectConfiguration) -> nx.DiGraph:
    """Build a DAG only after every declared prerequisite is known."""
    dag = nx.DiGraph()
    known_ids = set(config.experiments)
    for experiment_id, experiment in config.experiments.items():
        dag.add_node(experiment_id, experiment=experiment)
        for prerequisite in experiment.prerequisites:
            if prerequisite.experiment_id not in known_ids:
                raise ValueError(
                    f"Experiment '{experiment_id.value}' declares unknown prerequisite "
                    f"'{prerequisite.experiment_id.value}'"
                )
            dag.add_edge(prerequisite.experiment_id, experiment_id)
    if not nx.is_directed_acyclic_graph(dag):
        raise ValueError("Experiment dependency graph contains a cycle")
    return dag


def _canonical_experiment_order(config: ResolvedProjectConfiguration) -> tuple[ExperimentId, ...]:
    dag = _build_experiment_dag(config)
    remaining = set(dag.nodes())
    ordered: list[ExperimentId] = []
    while remaining:
        ready = [node for node in remaining if all(parent not in remaining for parent in dag.predecessors(node))]
        if not ready:
            raise ValueError("Experiment dependency graph contains a cycle")
        ready.sort(key=lambda node: (0 if _is_anchor(dag, node) else 1, node.value))
        ordered.extend(ready)
        remaining.difference_update(ready)
    return tuple(ordered)


def _is_anchor(dag: nx.DiGraph, experiment_id: ExperimentId) -> bool:
    experiment = dag.nodes[experiment_id]["experiment"]
    return experiment.evidence_role is EvidenceRole.ANCHOR


class CampaignOrchestrator:
    """Run one canonical campaign; never resume stage work or delete dependents."""

    def __init__(
        self,
        *,
        config: ResolvedProjectConfiguration,
        lifecycle: ExperimentLifecycleUseCase,
        output_manager: ExperimentOutputManager,
    ) -> None:
        self._config = config
        self._lifecycle = lifecycle
        self._output_manager = output_manager
        self._dag = _build_experiment_dag(config)
        self._order = _canonical_experiment_order(config)
        self._campaign_plan = expand_campaign_jobs(
            tuple(config.experiments[experiment_id] for experiment_id in self._order), config
        )
        validate_planning_graph(self._campaign_plan)

    @property
    def experiment_order(self) -> tuple[ExperimentId, ...]:
        return self._order

    @property
    def campaign_plan(self) -> PlanningGraph:
        """The one deterministic, planning-scoped campaign graph."""
        return self._campaign_plan

    def run(self, *, override_all: bool = False) -> CampaignReport:
        if override_all:
            for experiment_id in self._config.experiments:
                self._output_manager.delete(experiment_id)
            self._output_manager.delete_shared_outputs()
        return self._run()

    def _run(self) -> CampaignReport:
        runs = self._lifecycle.run_campaign(self._order)
        results = [
            CampaignExperimentResult(
                experiment_id=run.experiment_id,
                status=(
                    CampaignExperimentStatus.SKIPPED_EXISTING
                    if run.status is ExperimentRunStatus.SKIPPED_EXISTING
                    else CampaignExperimentStatus.EXECUTED
                    if run.status is ExperimentRunStatus.EXECUTED
                    else CampaignExperimentStatus.FAILED
                ),
                report=run.report,
                error_message=run.error_message,
            )
            for run in runs
        ]
        return self._build_report(results)

    @staticmethod
    def _requires_anchor(experiment: ExperimentRecord) -> bool:
        return any(
            prerequisite.required_outcome == "anchor_equivalence_passed" for prerequisite in experiment.prerequisites
        )

    def _anchor_passed(self, experiment_id: ExperimentId) -> bool:
        inspection = self._output_manager.inspect(experiment_id)
        if inspection.state is not OutputState.VALID_COMPLETED or inspection.manifest is None:
            return False
        frozen = self._output_manager.load_frozen_result(experiment_id, inspection.manifest)
        outcomes = frozen.get("outcomes")
        return frozen.get("anchor_equivalence_passed") is True or (
            isinstance(outcomes, dict) and outcomes.get("anchor_equivalence_passed") is True
        )

    @staticmethod
    def _prerequisite_error(
        experiment: ExperimentRecord,
        prior: dict[ExperimentId, CampaignExperimentResult],
    ) -> str | None:
        for prerequisite in experiment.prerequisites:
            result = prior.get(prerequisite.experiment_id)
            if result is None:
                return f"Prerequisite '{prerequisite.experiment_id.value}' was not processed"
            if result.status not in {
                CampaignExperimentStatus.EXECUTED,
                CampaignExperimentStatus.SKIPPED_EXISTING,
                CampaignExperimentStatus.INCOMPLETE_RESTARTED,
            }:
                return f"Prerequisite '{prerequisite.experiment_id.value}' did not complete successfully"
        return None

    @staticmethod
    def _build_report(results: list[CampaignExperimentResult]) -> CampaignReport:
        completed_or_skipped = sum(result.status is CampaignExperimentStatus.SKIPPED_EXISTING for result in results)
        executed = sum(
            result.status in {CampaignExperimentStatus.EXECUTED, CampaignExperimentStatus.INCOMPLETE_RESTARTED}
            for result in results
        )
        blocked = sum(
            result.status in {CampaignExperimentStatus.BLOCKED_PREREQUISITE, CampaignExperimentStatus.BLOCKED_ANCHOR}
            for result in results
        )
        failed = sum(
            result.status in {CampaignExperimentStatus.FAILED, CampaignExperimentStatus.INCOMPATIBLE}
            for result in results
        )
        return CampaignReport(
            results=tuple(results),
            total_experiments=len(results),
            completed_or_skipped=completed_or_skipped,
            executed=executed,
            blocked=blocked,
            failed=failed,
            success=failed == 0 and blocked == 0,
        )


__all__ = [
    "CampaignExperimentResult",
    "CampaignExperimentStatus",
    "CampaignOrchestrator",
    "CampaignReport",
    "_build_experiment_dag",
    "_canonical_experiment_order",
]
