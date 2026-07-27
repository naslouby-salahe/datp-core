"""Sequential campaign runner over validated experiment output folders."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time

import networkx as nx
from pydantic import TypeAdapter

from datp_core.analysis.contracts import AnalysisResult, AnchorEquivalenceAnalysisResult
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.freezing import FrozenResultManifest
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.catalogue.models import EvidenceRole, ExperimentRecord
from datp_core.experiments.execution.output_manager import ExperimentOutputManager, OutputState
from datp_core.experiments.execution.report import ExperimentExecutionReport
from datp_core.experiments.execution.runner import (
    ExecuteExperimentUseCase,
    _source_fingerprint,
)
from datp_core.experiments.planning.builder import ExperimentPlanBuilder
from datp_core.experiments.planning.compilation import compile_experiment
from datp_core.pipeline.stages.enums import JobExecutionStatus

_AnalysisResultAdapter = TypeAdapter(tuple[AnalysisResult, ...])


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


# ---------------------------------------------------------------------------
# DAG construction and canonical ordering
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# CampaignRunner
# ---------------------------------------------------------------------------


class CampaignRunner:
    """Run one canonical campaign with shared upstream outputs."""

    def __init__(
        self,
        *,
        config: ResolvedProjectConfiguration,
        plan_builder: ExperimentPlanBuilder,
        execute_experiment: ExecuteExperimentUseCase,
        output_manager: ExperimentOutputManager,
    ) -> None:
        self._config = config
        self._plan_builder = plan_builder
        self._execute_experiment = execute_experiment
        self._output_manager = output_manager
        self._dag = _build_experiment_dag(config)
        self._order = _canonical_experiment_order(config)

    @property
    def experiment_order(self) -> tuple[ExperimentId, ...]:
        return self._order

    def run(self, *, override_all: bool = False) -> CampaignReport:
        if override_all:
            for experiment_id in self._config.experiments:
                self._output_manager.delete(experiment_id)
            self._output_manager.delete_shared_outputs()
        return self._run()

    def _run(self) -> CampaignReport:
        """Execute experiments in canonical order with shared upstream outputs."""
        prepared: list[tuple[ExperimentId, float, str]] = []
        results: dict[ExperimentId, CampaignExperimentResult] = {}
        for experiment_id in self._order:
            experiment = self._config.experiments.get(experiment_id)
            source_fp = _source_fingerprint(experiment, self._config)
            inspection = self._output_manager.inspect(
                experiment_id,
                scientific_fingerprint=self._config.scientific_fingerprint.value,
                execution_fingerprint=self._config.execution_fingerprint.value,
                source_data_fingerprint=source_fp,
            )
            if inspection.state is OutputState.VALID_COMPLETED:
                results[experiment_id] = CampaignExperimentResult(
                    experiment_id=experiment_id,
                    status=CampaignExperimentStatus.SKIPPED_EXISTING,
                )
                continue
            if inspection.state is not OutputState.ABSENT:
                self._output_manager.delete(experiment_id)
            self._output_manager.begin(experiment_id)
            prepared.append((experiment_id, time(), source_fp))

        if not prepared:
            return self._build_report(list(results.values()))

        compiled_experiments = tuple(compile_experiment(self._config, eid) for eid, _, _ in prepared)
        graph = self._plan_builder.build_campaign(compiled_experiments)
        outcomes = self._execute_experiment.execute_graph(graph)
        jobs = {job.node_key: job for job in graph.jobs}

        for experiment_id, started_at, source_fp in prepared:
            experiment = self._config.experiments.get(experiment_id)
            owned = tuple(
                outcome for outcome in outcomes if jobs[outcome.node_key].context.experiment_id == experiment_id
            )
            failed = tuple(outcome for outcome in owned if outcome.status is not JobExecutionStatus.SUCCESS)
            report = ExperimentExecutionReport(
                experiment_id=experiment_id,
                outcomes=owned,
                successful_jobs=len(owned) - len(failed),
                failed_jobs=len(failed),
            )
            if failed:
                error = failed[0].error_message or "campaign dependency did not complete"
                self._output_manager.mark_failed(experiment_id, error)
                results[experiment_id] = CampaignExperimentResult(
                    experiment_id=experiment_id,
                    status=CampaignExperimentStatus.FAILED,
                    report=report,
                    error_message=error,
                )
                continue

            prerequisite_fingerprints = self._prerequisite_fingerprints(experiment, results)

            self._output_manager.finalize_from_directory(
                experiment_id,
                scientific_fingerprint=self._config.scientific_fingerprint.value,
                execution_fingerprint=self._config.execution_fingerprint.value,
                source_data_fingerprint=source_fp,
                prerequisite_result_fingerprints=prerequisite_fingerprints,
                started_at=started_at,
            )
            results[experiment_id] = CampaignExperimentResult(
                experiment_id=experiment_id,
                status=CampaignExperimentStatus.EXECUTED,
                report=report,
            )

        return self._build_report([results[experiment_id] for experiment_id in self._order])

    @staticmethod
    def _requires_anchor(experiment: ExperimentRecord) -> bool:
        return any(
            prerequisite.required_outcome == "anchor_equivalence_passed" for prerequisite in experiment.prerequisites
        )

    def _anchor_passed(self, experiment_id: ExperimentId) -> bool:
        inspection = self._output_manager.inspect(experiment_id)
        if inspection.state is not OutputState.VALID_COMPLETED or inspection.manifest is None:
            return False
        raw = self._output_manager.load_frozen_result(experiment_id, inspection.manifest)
        manifest = FrozenResultManifest.model_validate(raw)
        validated = _AnalysisResultAdapter.validate_python(manifest.statistical_results)
        for result in validated:
            if isinstance(result, AnchorEquivalenceAnalysisResult) and result.passed:
                return True
        return False

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

    def _prerequisite_fingerprints(
        self,
        experiment: ExperimentRecord,
        results: dict[ExperimentId, CampaignExperimentResult],
    ) -> dict[str, str]:
        """Collect frozen-result fingerprints for all declared prerequisites."""
        fingerprints: dict[str, str] = {}
        for prerequisite in experiment.prerequisites:
            prereq_manifest = self._output_manager.inspect(prerequisite.experiment_id).manifest
            if prereq_manifest is None:
                raise ValueError(
                    f"Campaign prerequisite '{prerequisite.experiment_id.value}' lacks a completed manifest"
                )
            fingerprints[prerequisite.experiment_id.value] = prereq_manifest.frozen_result_fingerprint
        return fingerprints

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
    "CampaignRunner",
    "CampaignReport",
    "_build_experiment_dag",
    "_canonical_experiment_order",
]
