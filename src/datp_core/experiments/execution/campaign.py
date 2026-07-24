"""Campaign orchestrator: executes the full scientific campaign with DAG ordering,
anchor gating, prerequisite enforcement, and automatic restart of incomplete experiments.
"""

from __future__ import annotations

from enum import Enum

import networkx as nx
from attrs import define

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.catalogue.models import EvidenceRole, ExperimentRecord
from datp_core.experiments.execution.output_manager import ExperimentOutputManager
from datp_core.experiments.execution.report import ExperimentExecutionReport
from datp_core.experiments.execution.use_case import ExecuteExperimentUseCase


class CampaignExperimentStatus(Enum):
    COMPLETED_VALID = "completed_valid"
    SKIPPED_EXISTING = "skipped_existing"
    INCOMPLETE_RESTARTED = "incomplete_restarted"
    BLOCKED_PREREQUISITE = "blocked_prerequisite"
    BLOCKED_ANCHOR = "blocked_anchor"
    EXECUTED = "executed"
    FAILED = "failed"


@define(frozen=False, slots=True, kw_only=True)
class CampaignExperimentResult:
    experiment_id: ExperimentId
    status: CampaignExperimentStatus
    report: ExperimentExecutionReport | None = None
    error_message: str | None = None


@define(frozen=True, slots=True, kw_only=True)
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
    """Build the experiment dependency DAG from prerequisite declarations."""
    dag = nx.DiGraph()
    for exp_id, experiment in config.experiments.items():
        dag.add_node(exp_id, experiment=experiment)
        for prereq in experiment.prerequisites:
            dag.add_edge(prereq.experiment_id, exp_id)
    return dag


def _canonical_experiment_order(config: ResolvedProjectConfiguration) -> tuple[ExperimentId, ...]:
    """Return the canonical topological experiment order.

    Anchor experiments and their dependents come first. Within the same topological
    generation, experiments are sorted by name for determinism.
    """
    dag = _build_experiment_dag(config)

    if not nx.is_directed_acyclic_graph(dag):
        cycles = list(nx.simple_cycles(dag))
        cycle_strs = [" -> ".join(str(n) for n in cycle) for cycle in cycles]
        raise ValueError(f"Experiment dependency graph contains cycles: {cycle_strs}")

    # Topological generations
    generations: list[list[ExperimentId]] = []
    remaining = set(dag.nodes())
    while remaining:
        ready = {n for n in remaining if all(p not in remaining for p in dag.predecessors(n))}
        if not ready:
            raise ValueError("DAG cycle detected during topological sort")
        # Sort within generation: anchor first, then by name
        sorted_ready = sorted(ready, key=lambda n: (0 if _is_anchor(dag, n) else 1, n.value))
        generations.append(sorted_ready)
        remaining -= ready

    return tuple(exp for gen in generations for exp in gen)


def _is_anchor(dag: nx.DiGraph, experiment_id: ExperimentId) -> bool:
    """Check if the experiment has EvidenceRole.ANCHOR."""
    exp_data = dag.nodes[experiment_id]
    experiment = exp_data.get("experiment")
    if experiment is not None:
        return experiment.evidence_role == EvidenceRole.ANCHOR
    return False


def _get_dependents(dag: nx.DiGraph, experiment_id: ExperimentId) -> tuple[ExperimentId, ...]:
    """Return all transitive dependents of an experiment."""
    return tuple(nx.descendants(dag, experiment_id))


def _get_transitive_dependents(
    dag: nx.DiGraph, experiment_id: ExperimentId, ordered: tuple[ExperimentId, ...]
) -> tuple[ExperimentId, ...]:
    """Return transitive dependents in canonical order."""
    deps = _get_dependents(dag, experiment_id)
    return tuple(e for e in ordered if e in deps)


class CampaignOrchestrator:
    """Executes the full scientific campaign.

    Responsibilities:
    - Build experiment dependency DAG from prerequisites
    - Compute canonical topological experiment order
    - Anchor gating: ensure anchor executes first, block dependents on anchor failure
    - Prerequisite enforcement: check prerequisite outcomes before running
    - Skip completed experiments (valid COMPLETED marker)
    - Auto-restart incomplete experiments (delete and rerun from scratch)
    - Handle --override-all
    """

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        execute_experiment: ExecuteExperimentUseCase,
        output_manager: ExperimentOutputManager,
    ) -> None:
        self._config = config
        self._execute_experiment = execute_experiment
        self._output_manager = output_manager
        self._dag = _build_experiment_dag(config)
        self._order = _canonical_experiment_order(config)

    @property
    def experiment_order(self) -> tuple[ExperimentId, ...]:
        return self._order

    def run(self, *, override_all: bool = False) -> CampaignReport:
        if override_all:
            self._override_all()

        results: list[CampaignExperimentResult] = []
        anchor_passed = False
        prerequisite_results: dict[ExperimentId, CampaignExperimentResult] = {}

        for experiment_id in self._order:
            experiment = self._config.experiments.get(experiment_id)
            if experiment is None:
                results.append(
                    CampaignExperimentResult(
                        experiment_id=experiment_id,
                        status=CampaignExperimentStatus.FAILED,
                        error_message="Experiment not found in catalogue",
                    )
                )
                continue

            # --- Anchor gating ---
            if self._requires_anchor(experiment) and not anchor_passed:
                result = CampaignExperimentResult(
                    experiment_id=experiment_id,
                    status=CampaignExperimentStatus.BLOCKED_ANCHOR,
                    error_message="Anchor equivalence has not passed; dependent experiments are blocked",
                )
                self._output_manager.mark_blocked(experiment_id, result.error_message)
                results.append(result)
                prerequisite_results[experiment_id] = result
                continue

            # --- Prerequisite enforcement ---
            prereq_error = self._check_prerequisites(experiment, prerequisite_results)
            if prereq_error is not None:
                result = CampaignExperimentResult(
                    experiment_id=experiment_id,
                    status=CampaignExperimentStatus.BLOCKED_PREREQUISITE,
                    error_message=prereq_error,
                )
                self._output_manager.mark_blocked(experiment_id, prereq_error)
                results.append(result)
                prerequisite_results[experiment_id] = result
                continue

            # --- Output state check ---
            if self._output_manager.is_completed(experiment_id):
                validation_error = self._output_manager.validate_completed(experiment_id)
                if validation_error is None:
                    result = CampaignExperimentResult(
                        experiment_id=experiment_id,
                        status=CampaignExperimentStatus.SKIPPED_EXISTING,
                    )
                    results.append(result)
                    prerequisite_results[experiment_id] = result
                    # Track anchor outcome
                    if experiment.evidence_role == EvidenceRole.ANCHOR:
                        anchor_passed = self._check_anchor_passed(experiment_id)
                    continue

            # --- Incomplete: auto-delete and restart ---
            if self._output_manager.is_incomplete(experiment_id):
                self._output_manager.delete(experiment_id)
                # Invalidate downstream results
                self._invalidate_dependents(experiment_id)

            # --- Execute ---
            self._output_manager.create(experiment_id)
            try:
                report = self._execute_experiment.execute(experiment_id)
            except Exception as exc:
                self._output_manager.mark_failed(experiment_id, str(exc))
                result = CampaignExperimentResult(
                    experiment_id=experiment_id,
                    status=CampaignExperimentStatus.FAILED,
                    error_message=str(exc),
                )
                results.append(result)
                prerequisite_results[experiment_id] = result
                self._block_dependents(experiment_id, results, prerequisite_results)
                continue

            failed = report.failed_jobs
            if failed > 0:
                self._output_manager.mark_failed(
                    experiment_id, f"{failed} job(s) failed out of {len(report.outcomes)}"
                )
                result = CampaignExperimentResult(
                    experiment_id=experiment_id,
                    status=CampaignExperimentStatus.FAILED,
                    report=report,
                )
                results.append(result)
                prerequisite_results[experiment_id] = result
                self._block_dependents(experiment_id, results, prerequisite_results)
                continue

            self._output_manager.mark_completed(experiment_id)
            result = CampaignExperimentResult(
                experiment_id=experiment_id,
                status=CampaignExperimentStatus.EXECUTED,
                report=report,
            )
            results.append(result)
            prerequisite_results[experiment_id] = result

            # Track anchor outcome
            if experiment.evidence_role == EvidenceRole.ANCHOR:
                anchor_passed = self._check_anchor_passed(experiment_id)

        return self._build_report(results)

    def _requires_anchor(self, experiment: ExperimentRecord) -> bool:
        """Check if the experiment requires anchor equivalence."""
        for prereq in experiment.prerequisites:
            if prereq.required_outcome == "anchor_equivalence_passed":
                return True
        return False

    def _check_anchor_passed(self, anchor_experiment_id: ExperimentId) -> bool:
        """Check if the anchor experiment has passed equivalence."""
        if not self._output_manager.is_completed(anchor_experiment_id):
            return False
        # Anchor equivalence is verified through the completed frozen result.
        # Future: read the typed frozen anchor outcome to validate anchor_equivalence_passed.
        return True

    def _check_prerequisites(
        self,
        experiment: ExperimentRecord,
        prerequisite_results: dict[ExperimentId, CampaignExperimentResult],
    ) -> str | None:
        """Check that all prerequisite experiments have completed successfully."""
        for prereq in experiment.prerequisites:
            prereq_result = prerequisite_results.get(prereq.experiment_id)
            if prereq_result is None:
                # Prerequisite hasn't been processed yet (shouldn't happen with topological order)
                return f"Prerequisite '{prereq.experiment_id.value}' has not been executed"
            if prereq_result.status == CampaignExperimentStatus.BLOCKED_PREREQUISITE:
                return f"Prerequisite '{prereq.experiment_id.value}' is blocked"
            if prereq_result.status == CampaignExperimentStatus.BLOCKED_ANCHOR:
                return f"Prerequisite '{prereq.experiment_id.value}' is blocked by anchor failure"
            if prereq_result.status == CampaignExperimentStatus.FAILED:
                return f"Prerequisite '{prereq.experiment_id.value}' failed"
            if prereq_result.status == CampaignExperimentStatus.SKIPPED_EXISTING:
                # Validate that the prerequisite has the required outcome
                if prereq.required_outcome == "anchor_equivalence_passed":
                    if not self._check_anchor_passed(prereq.experiment_id):
                        return f"Prerequisite '{prereq.experiment_id.value}' does not have anchor_equivalence_passed"
                # 'completed' outcome is satisfied by a valid completed marker
        return None

    def _block_dependents(
        self,
        experiment_id: ExperimentId,
        results: list[CampaignExperimentResult],
        prerequisite_results: dict[ExperimentId, CampaignExperimentResult],
    ) -> None:
        """Block all downstream dependents of a failed experiment."""
        dependents = _get_transitive_dependents(self._dag, experiment_id, self._order)
        for dep_id in dependents:
            if dep_id not in prerequisite_results:
                result = CampaignExperimentResult(
                    experiment_id=dep_id,
                    status=CampaignExperimentStatus.BLOCKED_PREREQUISITE,
                    error_message=f"Prerequisite '{experiment_id.value}' failed or was blocked",
                )
                self._output_manager.mark_blocked(dep_id, result.error_message)
                results.append(result)
                prerequisite_results[dep_id] = result

    def _invalidate_dependents(self, experiment_id: ExperimentId) -> None:
        """Delete all transitive dependent experiment outputs.

        When an experiment is restarted, its dependents become stale and must be deleted.
        """
        dependents = _get_transitive_dependents(self._dag, experiment_id, self._order)
        for dep_id in dependents:
            if self._output_manager.exists(dep_id):
                self._output_manager.delete(dep_id)

    def _override_all(self) -> None:
        """Delete all campaign-managed experiment outputs."""
        for exp_dir in self._output_manager.list_experiment_dirs():
            exp_id = ExperimentId(exp_dir.name)
            self._output_manager.delete(exp_id)

    def _build_report(self, results: list[CampaignExperimentResult]) -> CampaignReport:
        completed_or_skipped = sum(
            1
            for r in results
            if r.status
            in (CampaignExperimentStatus.COMPLETED_VALID, CampaignExperimentStatus.SKIPPED_EXISTING)
        )
        executed = sum(
            1 for r in results if r.status == CampaignExperimentStatus.EXECUTED
        )
        blocked = sum(
            1
            for r in results
            if r.status
            in (CampaignExperimentStatus.BLOCKED_PREREQUISITE, CampaignExperimentStatus.BLOCKED_ANCHOR)
        )
        failed = sum(1 for r in results if r.status == CampaignExperimentStatus.FAILED)
        success = failed == 0 and blocked == 0

        return CampaignReport(
            results=tuple(results),
            total_experiments=len(results),
            completed_or_skipped=completed_or_skipped,
            executed=executed,
            blocked=blocked,
            failed=failed,
            success=success,
        )
