"""Execute experiment use case."""

from __future__ import annotations

from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.catalogue.models import CapabilityRequirementRecord, ExperimentRecord
from datp_core.experiments.execution.report import ExperimentExecutionReport
from datp_core.experiments.identity.run_locator import resolve_experiment_run_id
from datp_core.experiments.planning.jobs import expand_experiment_jobs
from datp_core.experiments.planning.validation import validate_planning_graph
from datp_core.pipeline.execution.registry import StageHandlerRegistry
from datp_core.pipeline.execution.runner import run_planning_graph
from datp_core.pipeline.stages.enums import JobExecutionStatus
from datp_core.pipeline.stages.handlers import StageHandler


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


_KNOWN_PREREQUISITE_OUTCOMES: frozenset[str] = frozenset({
    "completed",
    "anchor_equivalence_passed",
    "faithful_reproduction_claim_forbidden",
    "quantitative_claim_gate_passed",
})


class ExecuteExperimentUseCase:
    def __init__(self, config: ResolvedProjectConfiguration, handlers: tuple[StageHandler, ...]) -> None:
        self._config = config
        self._registry = StageHandlerRegistry({handler.stage: handler for handler in handlers})

    def execute(self, experiment_id: ExperimentId) -> ExperimentExecutionReport:
        experiment = self._config.experiments.get(experiment_id)

        contract_error = _validate_experiment_runtime_contracts(experiment, self._config)
        if contract_error is not None:
            return ExperimentExecutionReport(
                run_id=resolve_experiment_run_id(self._config, experiment_id),
                experiment_id=experiment_id,
                outcomes=(),
                successful_jobs=0,
                reused_jobs=0,
                failed_jobs=1,
            )

        graph = expand_experiment_jobs(experiment, self._config)
        validate_planning_graph(graph)

        run_id = resolve_experiment_run_id(self._config, experiment_id)

        outcomes = run_planning_graph(graph, self._registry, run_id)

        return ExperimentExecutionReport(
            run_id=run_id,
            experiment_id=experiment_id,
            outcomes=outcomes,
            successful_jobs=sum(outcome.status is JobExecutionStatus.SUCCESS for outcome in outcomes),
            reused_jobs=sum(outcome.status is JobExecutionStatus.REUSED for outcome in outcomes),
            failed_jobs=sum(outcome.status is JobExecutionStatus.FAILED for outcome in outcomes),
        )
