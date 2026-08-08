"""Generic programme validation, planning, and dataset preparation services."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.app.contracts import OverwriteMode
from datp_core.data.registry import DatasetPublication
from datp_core.data.service import DatasetMaterializationRequest, materialize_datasets
from datp_core.core.errors import (
    ProtocolValidationError,
    ScientificContractError,
    UnknownIdentifierError,
    UnresolvedScientificValueError,
)
from datp_core.core.identifiers import DatasetId, ExperimentId, ExperimentReadiness, PopulationId
from datp_core.core.numeric import Seed
from datp_core.experiments.planning import (
    ExperimentPlan,
    PlanDisposition,
    PlanningEvidence,
    expand_experiment_plan,
    merge_experiment_plans,
)
from datp_core.experiments.anchor.spec import HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.protocols.calibration import require_calibration_subsample_replicate_count
from datp_core.protocols.experiments import EXPERIMENTS, ExperimentDeclaration
from datp_core.data.populations.declarations import POPULATIONS
from datp_core.experiments.common.seeds import BOUNDED_EVIDENCE_SEED_COHORT, CONFIRMATORY_SEED_COHORT, SeedCohort
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH, ResolvedProtocolGraph, validate_protocol_graph
from datp_core.runtime.configuration import DATA_ROOT


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationResult:
    graph: ResolvedProtocolGraph
    experiment_ids: tuple[ExperimentId, ...]
    registered_recipes: tuple[ExperimentId, ...]
    suppressed_experiments: tuple[ExperimentId, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanPresentation:
    plan: ExperimentPlan
    experiment_ids: tuple[ExperimentId, ...]
    seed_cohorts: tuple[tuple[ExperimentId, tuple[Seed, ...]], ...]
    anchor_required: tuple[ExperimentId, ...]
    registered_recipes: tuple[ExperimentId, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PreprocessResult:
    datasets: tuple[DatasetId, ...]
    publications: tuple[DatasetPublication, ...]


def require_experiment_declaration(experiment_id: ExperimentId) -> ExperimentDeclaration:
    matches = tuple(item for item in EXPERIMENTS if item.id is experiment_id)
    if len(matches) != 1:
        raise UnknownIdentifierError(
            f"experiment must be declared exactly once: {experiment_id.value}",
            subject=experiment_id,
        )
    return matches[0]


def reject_anchor_as_experiment(experiment_id: ExperimentId) -> None:
    if experiment_id is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        raise ScientificContractError(
            "historical anchor reproduction is not selectable as EXPERIMENT_ID; use anchor commands",
            subject=experiment_id,
        )


def require_experiment_execution_ready(experiment_id: ExperimentId) -> None:
    declaration = require_experiment_declaration(experiment_id)
    if declaration.readiness is ExperimentReadiness.SUPPRESSED:
        raise ScientificContractError(
            f"experiment is intentionally suppressed: {experiment_id.value}",
            subject=experiment_id,
        )
    if declaration.readiness is ExperimentReadiness.INFEASIBLE:
        raise ScientificContractError(
            f"experiment is scientifically infeasible: {experiment_id.value}",
            subject=experiment_id,
        )
    if declaration.readiness is ExperimentReadiness.BLOCKED:
        raise ScientificContractError(
            f"experiment is blocked by its declaration: {experiment_id.value}",
            subject=experiment_id,
        )
    if experiment_id is ExperimentId.CALIBRATION_SIZE_ABLATION:
        require_calibration_subsample_replicate_count()


def seed_cohort_for(experiment_id: ExperimentId) -> SeedCohort:
    declaration = require_experiment_declaration(experiment_id)
    if declaration.population in {
        PopulationId.EDGE_SENSOR_GROUPS,
        PopulationId.EDGE_TEMPORAL_GROUPS,
        PopulationId.CICIOT_FILE_CLIENTS,
    }:
        return BOUNDED_EVIDENCE_SEED_COHORT
    return CONFIRMATORY_SEED_COHORT


def executable_planning_evidence(experiment_id: ExperimentId) -> PlanningEvidence:
    return PlanningEvidence(
        experiment=experiment_id,
        disposition=PlanDisposition.EXECUTABLE,
        reason="registered experiment recipe supplies locked execution prerequisites from protocol declarations",
    )


def _planning_evidence(declaration: ExperimentDeclaration) -> tuple[PlanningEvidence, ...]:
    if declaration.readiness is ExperimentReadiness.SUPPRESSED:
        return ()
    if declaration.readiness is ExperimentReadiness.INFEASIBLE:
        return ()
    if declaration.readiness is ExperimentReadiness.BLOCKED:
        return ()
    try:
        require_experiment_execution_ready(declaration.id)
    except UnresolvedScientificValueError as error:
        return (
            PlanningEvidence(
                experiment=declaration.id,
                disposition=PlanDisposition.BLOCKED,
                reason=str(error),
            ),
        )
    return (executable_planning_evidence(declaration.id),)


def validate_programme(experiment_id: ExperimentId | None) -> ValidationResult:
    from datp_core.app.research import anchor_gated_experiment_ids, registered_experiment_ids

    graph = validate_protocol_graph(CANONICAL_PROTOCOL_GRAPH)
    registered = registered_experiment_ids()
    if len(registered) != len(frozenset(registered)):
        raise ProtocolValidationError("experiment recipe registry contains duplicate experiment identities")
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
            "experiment recipe registry must cover every non-suppressed experiment exactly once; "
            f"missing={','.join(item.value for item in missing) or 'none'}; "
            f"stale={','.join(item.value for item in stale) or 'none'}"
        )
    known_populations = frozenset(population.id for population in POPULATIONS)
    for declaration in graph.experiments:
        if declaration.population not in known_populations:
            raise ProtocolValidationError(f"experiment references unknown population: {declaration.id.value}")
    if experiment_id is None:
        experiment_ids = tuple(
            item.id for item in graph.experiments if item.id is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
        )
    else:
        reject_anchor_as_experiment(experiment_id)
        declaration = require_experiment_declaration(experiment_id)
        experiment_ids = (experiment_id,)
        if declaration.readiness is not ExperimentReadiness.SUPPRESSED and experiment_id not in registered:
            raise ProtocolValidationError(f"experiment has no registered recipe: {experiment_id.value}")
    suppressed = tuple(
        item
        for item in experiment_ids
        if require_experiment_declaration(item).readiness is ExperimentReadiness.SUPPRESSED
    )
    if any(item not in registered for item in anchor_gated_experiment_ids()):
        raise ProtocolValidationError("anchor-gated experiment set contains an unregistered recipe")
    return ValidationResult(
        graph=graph,
        experiment_ids=experiment_ids,
        registered_recipes=tuple(item for item in experiment_ids if item in frozenset(registered)),
        suppressed_experiments=suppressed,
    )


def _plan_for_declaration(declaration: ExperimentDeclaration) -> ExperimentPlan:
    if declaration.id is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        return expand_experiment_plan(
            declarations=(declaration,),
            seed_cohort=HISTORICAL_ANCHOR_SEED_COHORT,
            evidence=(
                PlanningEvidence(
                    experiment=declaration.id,
                    disposition=PlanDisposition.EXECUTABLE,
                    reason="historical anchor reproduction uses the locked historical seed cohort",
                ),
            ),
        )
    return expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=seed_cohort_for(declaration.id),
        evidence=_planning_evidence(declaration),
    )


def build_programme_plan(experiment_id: ExperimentId | None) -> PlanPresentation:
    from datp_core.app.research import anchor_gated_experiment_ids

    validation = validate_programme(experiment_id)
    declarations = EXPERIMENTS if experiment_id is None else (require_experiment_declaration(experiment_id),)
    plan = merge_experiment_plans(tuple(_plan_for_declaration(declaration) for declaration in declarations))
    experiment_ids = tuple(declaration.id for declaration in declarations)
    cohorts = tuple(
        (
            declaration.id,
            HISTORICAL_ANCHOR_SEED_COHORT.values
            if declaration.id is ExperimentId.HISTORICAL_DATP_REPRODUCTION
            else seed_cohort_for(declaration.id).values,
        )
        for declaration in declarations
    )
    anchor_required = tuple(item for item in experiment_ids if item in frozenset(anchor_gated_experiment_ids()))
    return PlanPresentation(
        plan=plan,
        experiment_ids=experiment_ids,
        seed_cohorts=cohorts,
        anchor_required=anchor_required,
        registered_recipes=validation.registered_recipes,
    )


def preprocess_datasets(
    dataset_id: DatasetId | None,
    *,
    overwrite: OverwriteMode,
) -> PreprocessResult:
    datasets = tuple(DatasetId) if dataset_id is None else (dataset_id,)
    result = materialize_datasets(
        DatasetMaterializationRequest(
            data_root=DATA_ROOT,
            datasets=datasets,
            overwrite=overwrite.requested,
        )
    )
    return PreprocessResult(datasets=datasets, publications=result.publications)


def format_plan(presentation: PlanPresentation) -> str:
    lines = [
        f"plan_digest={presentation.plan.digest.value}",
        f"entries={len(presentation.plan.entries)}",
        f"executable={len(presentation.plan.executable)}",
        f"experiments={','.join(item.value for item in presentation.experiment_ids)}",
        f"registered={','.join(item.value for item in presentation.registered_recipes)}",
        f"anchor_required={','.join(item.value for item in presentation.anchor_required)}",
    ]
    for experiment_id, seeds in presentation.seed_cohorts:
        lines.append(f"seeds[{experiment_id.value}]={','.join(str(seed.value) for seed in seeds)}")
    for disposition in PlanDisposition:
        count = sum(1 for entry in presentation.plan.entries if entry.disposition is disposition)
        if count:
            lines.append(f"disposition[{disposition.value}]={count}")
    return "\n".join(lines)
