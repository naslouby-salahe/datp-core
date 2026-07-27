"""Consolidated experiment runner: lifecycle, execution, and prerequisite outcome checks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time

from pydantic import TypeAdapter

from datp_core.analysis.comparisons.contracts import AnchorEquivalenceAnalysisResult
from datp_core.analysis.contracts import AnalysisResult, PrerequisiteExperimentResult
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.freezing import FrozenResultManifest
from datp_core.core.identifiers import ExperimentId
from datp_core.data.sources.inventory import compute_experiment_source_fingerprint
from datp_core.experiments.catalogue.models import CapabilityRequirementRecord, ExperimentRecord
from datp_core.experiments.execution import ExperimentExecutionReport
from datp_core.experiments.execution.output_manager import (
    ExperimentManifest,
    ExperimentOutputManager,
    OutputState,
)
from datp_core.experiments.planning.builder import ExperimentPlanBuilder
from datp_core.experiments.planning.compilation import compile_experiment
from datp_core.experiments.planning.validation import validate_planning_graph
from datp_core.pipeline.execution.registry import StageHandlerRegistry
from datp_core.pipeline.execution.runner import run_planning_graph
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.stages.enums import JobExecutionStatus
from datp_core.pipeline.stages.handlers import StageHandler
from datp_core.pipeline.stages.outcomes import StageJobOutcome

_AnalysisResultsAdapter = TypeAdapter(tuple[AnalysisResult, ...])


# Runtime-contract validation (pure, no side effects)


def _validate_capability_requirements(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
) -> str | None:
    for requirement in experiment.capability_requirements:
        if requirement.capability not in config.capabilities:
            return (
                f"Experiment '{experiment.identifier}' requires capability '{requirement.capability}' "
                f"which is not in the global capabilities list: {sorted(config.capabilities)}"
            )
        error = _validate_capability_populations(experiment, requirement, config)
        if error is not None:
            return error
    return None


def _validate_capability_populations(
    experiment: ExperimentRecord,
    requirement: CapabilityRequirementRecord,
    config: ResolvedProjectConfiguration,
) -> str | None:
    if requirement.applies_to_populations is None:
        return None
    for pop_id in requirement.applies_to_populations:
        population = config.populations.get(pop_id)
        if population is None:
            return (
                f"Experiment '{experiment.identifier}' capability '{requirement.capability}' "
                f"references unknown population '{pop_id}'"
            )
        dataset = config.datasets[population.dataset_id]
        if requirement.capability not in dataset.capabilities:
            return (
                f"Experiment '{experiment.identifier}' requires capability '{requirement.capability}' "
                f"for population '{pop_id}', but dataset '{population.dataset_id}' provides "
                f"capabilities: {sorted(dataset.capabilities)}"
            )
    return None


def _validate_prerequisites(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
) -> str | None:
    for prerequisite in experiment.prerequisites:
        try:
            config.experiments.get(prerequisite.experiment_id)
        except KeyError:
            return (
                f"Experiment '{experiment.identifier}' declares prerequisite "
                f"'{prerequisite.experiment_id}' which is not registered"
            )
        if prerequisite.required_outcome not in _KNOWN_PREREQUISITE_OUTCOMES:
            return (
                f"Experiment '{experiment.identifier}' prerequisite '{prerequisite.experiment_id}' "
                f"declares unknown required_outcome '{prerequisite.required_outcome}'; "
                f"known outcomes: {sorted(_KNOWN_PREREQUISITE_OUTCOMES)}"
            )
    return None


def _validate_experiment_runtime_contracts(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
) -> str | None:
    capability_error = _validate_capability_requirements(experiment, config)
    if capability_error is not None:
        return capability_error
    return _validate_prerequisites(experiment, config)


_COMPLETED_OUTCOME = "completed"
_ANCHOR_EQUIVALENCE_PASSED = "anchor_equivalence_passed"

_KNOWN_PREREQUISITE_OUTCOMES: frozenset[str] = frozenset(
    {
        _COMPLETED_OUTCOME,
        _ANCHOR_EQUIVALENCE_PASSED,
        "faithful_reproduction_claim_forbidden",
        "quantitative_claim_gate_passed",
    }
)


# Public result types


class ExperimentRunStatus(Enum):
    EXECUTED = "executed"
    SKIPPED_EXISTING = "skipped_existing"
    REJECTED_EXISTING = "rejected_existing"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ExperimentRunResult:
    experiment_id: ExperimentId
    status: ExperimentRunStatus
    report: ExperimentExecutionReport | None = None
    manifest: ExperimentManifest | None = None
    error_message: str | None = None

    @property
    def success(self) -> bool:
        return self.status in {ExperimentRunStatus.EXECUTED, ExperimentRunStatus.SKIPPED_EXISTING}


# Prerequisite outcome helpers


def _prerequisite_outcome_satisfied(
    statistical_results: tuple[AnalysisResult, ...],
    required_outcome: str,
) -> bool:
    """Check whether validated analysis results satisfy *required_outcome*."""
    if required_outcome == _COMPLETED_OUTCOME:
        return True
    for result in statistical_results:
        if isinstance(result, AnchorEquivalenceAnalysisResult) and result.passed:
            return True
        if (
            required_outcome not in (_COMPLETED_OUTCOME, _ANCHOR_EQUIVALENCE_PASSED)
            and result.result_kind.value == required_outcome
        ):
            return True
    return False


def _source_fingerprint(
    experiment: ExperimentRecord,
    config: ResolvedProjectConfiguration,
) -> str:
    dataset_ids = tuple(
        dict.fromkeys(config.populations.get(population_id).dataset_id for population_id in experiment.population_ids)
    )
    return compute_experiment_source_fingerprint(datasets=config.datasets, dataset_ids=dataset_ids).value


def _load_prerequisite_results(
    experiment: ExperimentRecord,
    output_manager: ExperimentOutputManager,
) -> tuple[PrerequisiteExperimentResult, ...]:
    """Validate and load prerequisite frozen results for *experiment*."""
    results: list[PrerequisiteExperimentResult] = []
    for prerequisite in experiment.prerequisites:
        inspection = output_manager.inspect(prerequisite.experiment_id)
        if inspection.state is not OutputState.VALID_COMPLETED or inspection.manifest is None:
            raise ValueError(f"Prerequisite '{prerequisite.experiment_id.value}' is not a valid completed experiment")
        raw = output_manager.load_frozen_result(prerequisite.experiment_id, inspection.manifest)
        manifest = FrozenResultManifest.model_validate(raw)
        validated_results = _AnalysisResultsAdapter.validate_python(manifest.statistical_results)
        if not _prerequisite_outcome_satisfied(validated_results, prerequisite.required_outcome):
            raise ValueError(
                f"Prerequisite '{prerequisite.experiment_id.value}' does not satisfy '{prerequisite.required_outcome}'"
            )
        results.append(
            PrerequisiteExperimentResult(
                experiment_id=prerequisite.experiment_id,
                frozen_result_path=inspection.manifest.frozen_result_path,
                frozen_result_checksum=inspection.manifest.frozen_result_fingerprint,
                scientific_fingerprint=inspection.manifest.scientific_fingerprint,
                statistical_results=validated_results,
            )
        )
    return tuple(results)


# ExecuteExperimentUseCase -- graph expansion and execution


class ExecuteExperimentUseCase:
    """Expand and execute the planning graph for one experiment."""

    def __init__(
        self,
        config: ResolvedProjectConfiguration,
        plan_builder: ExperimentPlanBuilder,
        handlers: tuple[StageHandler, ...],
    ) -> None:
        self._config = config
        self._plan_builder = plan_builder
        self._registry = StageHandlerRegistry({handler.stage: handler for handler in handlers})

    @property
    def handler_registry(self) -> StageHandlerRegistry:
        """Public access to the stage handler registry for orchestration use."""
        return self._registry

    def execute(
        self,
        experiment_id: ExperimentId,
        *,
        prerequisite_results: tuple[PrerequisiteExperimentResult, ...] = (),
    ) -> ExperimentExecutionReport:
        experiment = self._config.experiments.get(experiment_id)

        contract_error = _validate_experiment_runtime_contracts(experiment, self._config)
        if contract_error is not None:
            return ExperimentExecutionReport(
                experiment_id=experiment_id,
                outcomes=(),
                successful_jobs=0,
                failed_jobs=1,
            )

        compiled = compile_experiment(self._config, experiment_id)
        graph = self._plan_builder.build(compiled, prerequisite_results=prerequisite_results)
        validate_planning_graph(graph)

        outcomes = run_planning_graph(graph, self._registry)

        return ExperimentExecutionReport(
            experiment_id=experiment_id,
            outcomes=outcomes,
            successful_jobs=sum(outcome.status is JobExecutionStatus.SUCCESS for outcome in outcomes),
            failed_jobs=sum(outcome.status is JobExecutionStatus.FAILED for outcome in outcomes),
        )

    def execute_graph(self, graph: PlanningGraph) -> tuple[StageJobOutcome, ...]:
        validate_planning_graph(graph)
        return run_planning_graph(graph, self._registry)


# ExperimentRunner -- lifecycle around one experiment


class ExperimentRunner:
    """Apply lifecycle rules around one fresh graph execution."""

    def __init__(
        self,
        *,
        config: ResolvedProjectConfiguration,
        execute_experiment: ExecuteExperimentUseCase,
        output_manager: ExperimentOutputManager,
    ) -> None:
        self._config = config
        self._execute_experiment = execute_experiment
        self._output_manager = output_manager

    def run(
        self,
        experiment_id: ExperimentId,
        *,
        override: bool = False,
    ) -> ExperimentRunResult:
        try:
            experiment = self._config.experiments.get(experiment_id)
        except KeyError:
            return ExperimentRunResult(
                experiment_id=experiment_id,
                status=ExperimentRunStatus.FAILED,
                error_message=f"Unknown configured experiment '{experiment_id.value}'",
            )
        try:
            prerequisite_results = _load_prerequisite_results(experiment, self._output_manager)
            prerequisite_fingerprints = {
                result.experiment_id.value: result.frozen_result_checksum for result in prerequisite_results
            }
            source_fp = _source_fingerprint(experiment, self._config)
        except ValueError as exc:
            return ExperimentRunResult(
                experiment_id=experiment_id,
                status=ExperimentRunStatus.FAILED,
                error_message=str(exc),
            )

        inspection = self._output_manager.inspect(
            experiment_id,
            scientific_fingerprint=self._config.scientific_fingerprint.value,
            execution_fingerprint=self._config.execution_fingerprint.value,
            source_data_fingerprint=source_fp,
            prerequisite_result_fingerprints=prerequisite_fingerprints,
        )
        if inspection.state is OutputState.VALID_COMPLETED and not override:
            return ExperimentRunResult(
                experiment_id=experiment_id,
                status=ExperimentRunStatus.SKIPPED_EXISTING,
                manifest=inspection.manifest,
            )
        if inspection.state is not OutputState.ABSENT and not override:
            return ExperimentRunResult(
                experiment_id=experiment_id,
                status=ExperimentRunStatus.REJECTED_EXISTING,
                error_message=(
                    f"Experiment '{experiment_id.value}' has {inspection.state.value} output"
                    f" ({inspection.reason or 'no validation detail'}); "
                    f"use --override to rerun from preflight"
                ),
            )
        if inspection.state is not OutputState.ABSENT:
            self._output_manager.delete(experiment_id)

        started_at = time()
        self._output_manager.begin(experiment_id)
        try:
            report = self._execute_experiment.execute(experiment_id, prerequisite_results=prerequisite_results)
            if report.failed_jobs:
                error = f"{report.failed_jobs} job(s) failed out of {len(report.outcomes)}"
                self._output_manager.mark_failed(experiment_id, error)
                return ExperimentRunResult(
                    experiment_id=experiment_id,
                    status=ExperimentRunStatus.FAILED,
                    report=report,
                    error_message=error,
                )
            manifest = self._output_manager.finalize_from_directory(
                experiment_id,
                scientific_fingerprint=self._config.scientific_fingerprint.value,
                execution_fingerprint=self._config.execution_fingerprint.value,
                source_data_fingerprint=source_fp,
                prerequisite_result_fingerprints=prerequisite_fingerprints,
                started_at=started_at,
            )
        except (OSError, ValueError, KeyError) as exc:
            self._output_manager.mark_failed(experiment_id, str(exc))
            return ExperimentRunResult(
                experiment_id=experiment_id,
                status=ExperimentRunStatus.FAILED,
                error_message=str(exc),
            )
        return ExperimentRunResult(
            experiment_id=experiment_id,
            status=ExperimentRunStatus.EXECUTED,
            report=report,
            manifest=manifest,
        )


__all__ = [
    "ExecuteExperimentUseCase",
    "ExperimentRunResult",
    "ExperimentRunStatus",
    "ExperimentRunner",
    "_ANCHOR_EQUIVALENCE_PASSED",
    "_COMPLETED_OUTCOME",
    "_KNOWN_PREREQUISITE_OUTCOMES",
    "_prerequisite_outcome_satisfied",
    "_source_fingerprint",
    "_load_prerequisite_results",
]
