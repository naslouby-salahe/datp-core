"""Research-facing programme services composed from typed experiment workflows.

Public CLI commands call these entry points, plus the campaign, reporting, and
status orchestration re-exported from :mod:`datp_core.pipeline.workflows.campaign`.
Experiment-specific scientific behaviour remains in the dedicated workflow
modules; this module owns generic protocol validation, planning, and
seed-cohort selection shared by every registered workflow.
"""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.datasets.service import DatasetMaterializationRequest, materialize_datasets
from datp_core.domain.enums import (
    DatasetId,
    ExperimentId,
    ExperimentReadiness,
    PopulationId,
)
from datp_core.domain.errors import (
    ProtocolValidationError,
    ScientificContractError,
    UnknownIdentifierError,
)
from datp_core.pipeline.planning import (
    ExperimentPlan,
    PlanDisposition,
    PlanningEvidence,
    expand_experiment_plan,
)
from datp_core.pipeline.workflows.campaign import (
    ANCHOR_GATED_EXPERIMENTS,
    REGISTERED_WORKFLOW_EXPERIMENTS,
    AnchorCommandResult,
    CampaignRunResult,
    ExperimentRunResult,
    ExperimentStatusRecord,
    ProgrammeStatusReport,
    ReportResult,
    anchor_status,
    format_plan,
    format_status,
    generate_report,
    programme_status,
    reproduce_anchor,
    run_campaign,
    run_experiment,
    run_smoke,
    verify_anchor_programme,
)
from datp_core.protocols.experiments import EXPERIMENTS, ExperimentDeclaration
from datp_core.protocols.populations import POPULATIONS
from datp_core.protocols.seeds import (
    BOUNDED_EVIDENCE_SEED_COHORT,
    CONFIRMATORY_SEED_COHORT,
    SeedCohort,
)
from datp_core.protocols.validation import CANONICAL_PROTOCOL_GRAPH, ResolvedProtocolGraph, validate_protocol_graph
from datp_core.runtime.configuration import DATA_ROOT


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidationResult:
    graph: ResolvedProtocolGraph
    experiment_ids: tuple[ExperimentId, ...]
    registered_workflows: tuple[ExperimentId, ...]
    unregistered_declared: tuple[ExperimentId, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanPresentation:
    plan: ExperimentPlan
    experiment_ids: tuple[ExperimentId, ...]
    seed_cohorts: tuple[tuple[ExperimentId, tuple[int, ...]], ...]
    anchor_required: tuple[ExperimentId, ...]
    registered_workflows: tuple[ExperimentId, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class PreprocessResult:
    datasets: tuple[DatasetId, ...]
    publications: tuple[str, ...]


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
        reason="registered workflow entry supplies locked execution prerequisites from protocol declarations",
    )


def validate_programme(experiment_id: ExperimentId | None = None) -> ValidationResult:
    graph = validate_protocol_graph(CANONICAL_PROTOCOL_GRAPH)
    if experiment_id is None:
        experiment_ids = tuple(
            item.id for item in graph.experiments if item.id is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
        )
    else:
        reject_anchor_as_experiment(experiment_id)
        require_experiment_declaration(experiment_id)
        experiment_ids = (experiment_id,)
        _ = expand_experiment_plan(
            declarations=(require_experiment_declaration(experiment_id),),
            seed_cohort=seed_cohort_for(experiment_id),
        )
    registered = tuple(item for item in experiment_ids if item in REGISTERED_WORKFLOW_EXPERIMENTS)
    unregistered = tuple(
        item
        for item in experiment_ids
        if item not in REGISTERED_WORKFLOW_EXPERIMENTS
        and item is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
        and require_experiment_declaration(item).readiness is not ExperimentReadiness.SUPPRESSED
    )
    for experiment in experiment_ids:
        if experiment is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
            continue
        declaration = require_experiment_declaration(experiment)
        if declaration.population not in {population.id for population in POPULATIONS}:
            raise ProtocolValidationError("experiment references an unknown population")
    return ValidationResult(
        graph=graph,
        experiment_ids=experiment_ids,
        registered_workflows=registered,
        unregistered_declared=unregistered,
    )


def build_programme_plan(experiment_id: ExperimentId | None = None) -> PlanPresentation:
    validate_programme(experiment_id)
    if experiment_id is None:
        declarations = EXPERIMENTS
        evidence = tuple(
            executable_planning_evidence(item.id) for item in EXPERIMENTS if item.id in REGISTERED_WORKFLOW_EXPERIMENTS
        )
        plan = expand_experiment_plan(declarations=declarations, evidence=evidence)
        experiment_ids = tuple(item.id for item in EXPERIMENTS)
    else:
        reject_anchor_as_experiment(experiment_id)
        declaration = require_experiment_declaration(experiment_id)
        evidence = (
            (executable_planning_evidence(experiment_id),) if experiment_id in REGISTERED_WORKFLOW_EXPERIMENTS else ()
        )
        plan = expand_experiment_plan(
            declarations=(declaration,),
            seed_cohort=seed_cohort_for(experiment_id),
            evidence=evidence,
        )
        experiment_ids = (experiment_id,)
    cohorts = tuple(
        (item, tuple(seed.value for seed in seed_cohort_for(item).values))
        for item in experiment_ids
        if item is not ExperimentId.HISTORICAL_DATP_REPRODUCTION
    )
    anchor_required = tuple(item for item in experiment_ids if item in ANCHOR_GATED_EXPERIMENTS)
    registered = tuple(item for item in experiment_ids if item in REGISTERED_WORKFLOW_EXPERIMENTS)
    return PlanPresentation(
        plan=plan,
        experiment_ids=experiment_ids,
        seed_cohorts=cohorts,
        anchor_required=anchor_required,
        registered_workflows=registered,
    )


def preprocess_datasets(
    dataset_id: DatasetId | None = None,
    *,
    overwrite: bool = False,
) -> PreprocessResult:
    datasets = tuple(DatasetId) if dataset_id is None else (dataset_id,)
    result = materialize_datasets(
        DatasetMaterializationRequest(data_root=DATA_ROOT, datasets=datasets, overwrite=overwrite)
    )
    publications = tuple(
        f"{publication.dataset.value}:{publication.publication_status.value}" for publication in result.publications
    )
    return PreprocessResult(datasets=datasets, publications=publications)


__all__ = [
    "AnchorCommandResult",
    "CampaignRunResult",
    "ExperimentRunResult",
    "ExperimentStatusRecord",
    "PlanPresentation",
    "PreprocessResult",
    "ProgrammeStatusReport",
    "ReportResult",
    "ValidationResult",
    "anchor_status",
    "build_programme_plan",
    "format_plan",
    "format_status",
    "generate_report",
    "preprocess_datasets",
    "programme_status",
    "reproduce_anchor",
    "run_campaign",
    "run_experiment",
    "run_smoke",
    "validate_programme",
    "verify_anchor_programme",
]
