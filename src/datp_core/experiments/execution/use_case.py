"""Execute experiment use case."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time

from datp_core.analysis.execution.inputs import PrerequisiteExperimentResult
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.freezing import decode_manifest
from datp_core.core.identifiers import ExperimentId
from datp_core.data.sources.inventory import compute_experiment_source_fingerprint
from datp_core.experiments.catalogue.models import CapabilityRequirementRecord, ExperimentRecord
from datp_core.experiments.execution.output_manager import (
    ExperimentManifest,
    ExperimentOutputManager,
    OutputState,
)
from datp_core.experiments.execution.report import ExperimentExecutionReport
from datp_core.experiments.planning.jobs import expand_campaign_jobs, expand_experiment_jobs
from datp_core.experiments.planning.validation import validate_planning_graph
from datp_core.pipeline.execution.registry import StageHandlerRegistry
from datp_core.pipeline.execution.runner import run_planning_graph
from datp_core.pipeline.graph.model import PlanningGraph
from datp_core.pipeline.stages.enums import JobExecutionStatus
from datp_core.pipeline.stages.handlers import StageHandler
from datp_core.pipeline.stages.outcomes import StageJobOutcome


def _validate_capability_requirements(experiment: ExperimentRecord, config: ResolvedProjectConfiguration) -> str | None:
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


def _validate_prerequisites(experiment: ExperimentRecord, config: ResolvedProjectConfiguration) -> str | None:
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
    experiment: ExperimentRecord, config: ResolvedProjectConfiguration
) -> str | None:
    capability_error = _validate_capability_requirements(experiment, config)
    if capability_error is not None:
        return capability_error
    return _validate_prerequisites(experiment, config)


_KNOWN_PREREQUISITE_OUTCOMES: frozenset[str] = frozenset(
    {
        "completed",
        "anchor_equivalence_passed",
        "faithful_reproduction_claim_forbidden",
        "quantitative_claim_gate_passed",
    }
)


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


class ExperimentLifecycleUseCase:
    """Apply standalone lifecycle rules around one fresh graph execution."""

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
            prerequisite_results = self._validated_prerequisite_results(experiment)
            prerequisite_fingerprints = {
                result.experiment_id.value: result.frozen_result_checksum for result in prerequisite_results
            }
            source_fingerprint = self._source_fingerprint(experiment)
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
            source_data_fingerprint=source_fingerprint,
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
                    f" ({inspection.reason or 'no validation detail'}); use --override to rerun from preflight"
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
                source_data_fingerprint=source_fingerprint,
                prerequisite_result_fingerprints=prerequisite_fingerprints,
                started_at=started_at,
            )
        except Exception as exc:
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

    def run_campaign(self, experiment_ids: tuple[ExperimentId, ...]) -> tuple[ExperimentRunResult, ...]:
        """Execute one combined campaign graph; standalone execution never enters here."""
        prepared: list[tuple[ExperimentRecord, float, str]] = []
        results: dict[ExperimentId, ExperimentRunResult] = {}
        for experiment_id in experiment_ids:
            experiment = self._config.experiments.get(experiment_id)
            source_fingerprint = self._source_fingerprint(experiment)
            inspection = self._output_manager.inspect(
                experiment_id,
                scientific_fingerprint=self._config.scientific_fingerprint.value,
                execution_fingerprint=self._config.execution_fingerprint.value,
                source_data_fingerprint=source_fingerprint,
            )
            if inspection.state is OutputState.VALID_COMPLETED:
                results[experiment_id] = ExperimentRunResult(
                    experiment_id=experiment_id,
                    status=ExperimentRunStatus.SKIPPED_EXISTING,
                    manifest=inspection.manifest,
                )
                continue
            if inspection.state is not OutputState.ABSENT:
                self._output_manager.delete(experiment_id)
            self._output_manager.begin(experiment_id)
            prepared.append((experiment, time(), source_fingerprint))
        if not prepared:
            return tuple(results[experiment_id] for experiment_id in experiment_ids)
        graph = expand_campaign_jobs(tuple(item[0] for item in prepared), self._config)
        outcomes = self._execute_experiment.execute_graph(graph)
        jobs = {job.node_key: job for job in graph.jobs}
        for experiment, started_at, source_fingerprint in prepared:
            owned = tuple(
                outcome for outcome in outcomes if jobs[outcome.node_key].context.experiment_id == experiment.identifier
            )
            failed = tuple(outcome for outcome in owned if outcome.status is not JobExecutionStatus.SUCCESS)
            report = ExperimentExecutionReport(
                experiment_id=experiment.identifier,
                outcomes=owned,
                successful_jobs=len(owned) - len(failed),
                failed_jobs=len(failed),
            )
            if failed:
                error = failed[0].error_message or "campaign dependency did not complete"
                self._output_manager.mark_failed(experiment.identifier, error)
                results[experiment.identifier] = ExperimentRunResult(
                    experiment_id=experiment.identifier,
                    status=ExperimentRunStatus.FAILED,
                    report=report,
                    error_message=error,
                )
                continue
            prerequisite_fingerprints = {
                prerequisite.experiment_id.value: self._required_campaign_manifest(
                    prerequisite.experiment_id, results
                ).frozen_result_fingerprint
                for prerequisite in experiment.prerequisites
            }
            manifest = self._output_manager.finalize_from_directory(
                experiment.identifier,
                scientific_fingerprint=self._config.scientific_fingerprint.value,
                execution_fingerprint=self._config.execution_fingerprint.value,
                source_data_fingerprint=source_fingerprint,
                prerequisite_result_fingerprints=prerequisite_fingerprints,
                started_at=started_at,
            )
            results[experiment.identifier] = ExperimentRunResult(
                experiment_id=experiment.identifier,
                status=ExperimentRunStatus.EXECUTED,
                report=report,
                manifest=manifest,
            )
        return tuple(results[experiment_id] for experiment_id in experiment_ids)

    @staticmethod
    def _required_campaign_manifest(
        experiment_id: ExperimentId, results: dict[ExperimentId, ExperimentRunResult]
    ) -> ExperimentManifest:
        result = results.get(experiment_id)
        if result is None or result.manifest is None:
            raise ValueError(f"Campaign prerequisite '{experiment_id.value}' lacks a completed manifest")
        return result.manifest

    def _validated_prerequisite_results(self, experiment: ExperimentRecord) -> tuple[PrerequisiteExperimentResult, ...]:
        results: list[PrerequisiteExperimentResult] = []
        for prerequisite in experiment.prerequisites:
            inspection = self._output_manager.inspect(prerequisite.experiment_id)
            if inspection.state is not OutputState.VALID_COMPLETED or inspection.manifest is None:
                raise ValueError(
                    f"Prerequisite '{prerequisite.experiment_id.value}' is not a valid completed experiment"
                )
            frozen = self._output_manager.load_frozen_result(prerequisite.experiment_id, inspection.manifest)
            if not self._outcome_is_satisfied(prerequisite.required_outcome, frozen):
                raise ValueError(
                    f"Prerequisite '{prerequisite.experiment_id.value}' does not satisfy "
                    f"'{prerequisite.required_outcome}'"
                )
            results.append(
                PrerequisiteExperimentResult(
                    experiment_id=prerequisite.experiment_id,
                    frozen_result_path=inspection.manifest.frozen_result_path,
                    frozen_result_checksum=inspection.manifest.frozen_result_fingerprint,
                    scientific_fingerprint=inspection.manifest.scientific_fingerprint,
                    result=decode_manifest(
                        (
                            self._output_manager.experiment_dir(prerequisite.experiment_id)
                            / inspection.manifest.frozen_result_path
                        ).read_bytes()
                    ),
                )
            )
        return tuple(results)

    @staticmethod
    def _outcome_is_satisfied(required_outcome: str, frozen_result: dict[str, object]) -> bool:
        if required_outcome == "completed":
            return True
        if frozen_result.get(required_outcome) is True:
            return True
        outcomes = frozen_result.get("outcomes")
        return isinstance(outcomes, dict) and outcomes.get(required_outcome) is True

    def _source_fingerprint(self, experiment: ExperimentRecord) -> str:
        dataset_ids = tuple(
            dict.fromkeys(
                self._config.populations.get(population_id).dataset_id for population_id in experiment.population_ids
            )
        )
        return compute_experiment_source_fingerprint(datasets=self._config.datasets, dataset_ids=dataset_ids).value


class ExecuteExperimentUseCase:
    def __init__(self, config: ResolvedProjectConfiguration, handlers: tuple[StageHandler, ...]) -> None:
        self._config = config
        self._registry = StageHandlerRegistry({handler.stage: handler for handler in handlers})

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

        graph = expand_experiment_jobs(experiment, self._config, prerequisite_results=prerequisite_results)
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
