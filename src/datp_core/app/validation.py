"""Programme validation contracts and application-level scientific checks."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.core.errors import (
    ErrorMessage,
    ProtocolValidationError,
    ScientificContractError,
    UnknownIdentifierError,
)
from datp_core.core.identifiers import ExperimentId, ExperimentReadiness
from datp_core.data.populations.declarations import POPULATIONS
from datp_core.experiments.graph import (
    CANONICAL_PROTOCOL_GRAPH,
    ResolvedProtocolGraph,
    validate_protocol_graph,
)
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
from datp_core.thresholds.protocols import require_calibration_subsample_replicate_count


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationResult:
    graph: ResolvedProtocolGraph
    experiment_ids: tuple[ExperimentId, ...]
    registered_recipes: tuple[ExperimentId, ...]
    suppressed_experiments: tuple[ExperimentId, ...]


def require_experiment_declaration(experiment_id: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    if len(matches) != 1:
        raise UnknownIdentifierError(
            ErrorMessage(f"experiment must be declared exactly once: {experiment_id.value}"),
            subject=experiment_id,
        )
    return matches[0]


def reject_anchor_as_experiment(experiment_id: ExperimentId) -> None:
    if experiment_id is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        raise ScientificContractError(
            ErrorMessage("historical anchor reproduction is not selectable as EXPERIMENT_ID; use anchor commands"),
            subject=experiment_id,
        )


def require_experiment_execution_ready(experiment_id: ExperimentId) -> None:
    declaration = require_experiment_declaration(experiment_id)
    if declaration.readiness is ExperimentReadiness.SUPPRESSED:
        raise ScientificContractError(
            ErrorMessage(f"experiment is intentionally suppressed: {experiment_id.value}"),
            subject=experiment_id,
        )
    if declaration.readiness is ExperimentReadiness.INFEASIBLE:
        raise ScientificContractError(
            ErrorMessage(f"experiment is scientifically infeasible: {experiment_id.value}"),
            subject=experiment_id,
        )
    if declaration.readiness is ExperimentReadiness.BLOCKED:
        raise ScientificContractError(
            ErrorMessage(f"experiment is blocked by its declaration: {experiment_id.value}"),
            subject=experiment_id,
        )
    if experiment_id is ExperimentId.CALIBRATION_SIZE_ABLATION:
        require_calibration_subsample_replicate_count()


def validate_programme(experiment_id: ExperimentId | None) -> ValidationResult:
    from datp_core.app.research import anchor_gated_experiment_ids, registered_experiment_ids

    graph = validate_protocol_graph(CANONICAL_PROTOCOL_GRAPH)
    registered = registered_experiment_ids()
    if len(registered) != len(frozenset(registered)):
        raise ProtocolValidationError(
            ErrorMessage("experiment recipe registry contains duplicate experiment identities")
        )
    declared_runnable = tuple(
        item.id
        for item in graph.experiments
        if item.id is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
        and item.readiness is not ExperimentReadiness.SUPPRESSED
    )
    if frozenset(registered) != frozenset(declared_runnable):
        missing = tuple(item for item in declared_runnable if item not in frozenset(registered))
        stale = tuple(item for item in registered if item not in frozenset(declared_runnable))
        raise ProtocolValidationError(
            ErrorMessage(
                "experiment recipe registry must cover every non-suppressed experiment exactly once; "
                f"missing={','.join(item.value for item in missing) or 'none'}; "
                f"stale={','.join(item.value for item in stale) or 'none'}"
            )
        )
    known_populations = frozenset(population.id for population in POPULATIONS)
    for declaration in graph.experiments:
        if declaration.population not in known_populations:
            raise ProtocolValidationError(
                ErrorMessage(f"experiment references unknown population: {declaration.id.value}")
            )
    if experiment_id is None:
        experiment_ids = tuple(
            item.id for item in graph.experiments if item.id is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
        )
    else:
        reject_anchor_as_experiment(experiment_id)
        declaration = require_experiment_declaration(experiment_id)
        experiment_ids = (experiment_id,)
        if declaration.readiness is not ExperimentReadiness.SUPPRESSED and experiment_id not in registered:
            raise ProtocolValidationError(ErrorMessage(f"experiment has no registered recipe: {experiment_id.value}"))
    suppressed = tuple(
        item
        for item in experiment_ids
        if require_experiment_declaration(item).readiness is ExperimentReadiness.SUPPRESSED
    )
    if any(item not in registered for item in anchor_gated_experiment_ids()):
        raise ProtocolValidationError(ErrorMessage("anchor-gated experiment set contains an unregistered recipe"))
    return ValidationResult(
        graph=graph,
        experiment_ids=experiment_ids,
        registered_recipes=tuple(item for item in experiment_ids if item in frozenset(registered)),
        suppressed_experiments=suppressed,
    )
