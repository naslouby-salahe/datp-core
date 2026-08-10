from __future__ import annotations

from dataclasses import dataclass

from datp_core.app.contracts import OverwriteMode
from datp_core.app.models import DetailText
from datp_core.app.planning import (
    ExperimentPlan,
    PlanDisposition,
    PlanningEvidence,
    PlanReason,
    expand_experiment_plan,
    merge_experiment_plans,
)
from datp_core.app.planning import (
    seed_cohort_for as _seed_cohort_for,
)
from datp_core.app.recipes import anchor_gated_experiment_ids
from datp_core.app.validation import (
    require_experiment_declaration,
    require_experiment_execution_ready,
    validate_programme,
)
from datp_core.core.errors import UnresolvedScientificValueError
from datp_core.core.identifiers import DatasetId, ExperimentId, ExperimentReadiness
from datp_core.core.numeric import Seed
from datp_core.data.registry import DatasetPublication
from datp_core.data.service import DatasetMaterializationRequest, materialize_datasets
from datp_core.experiments.anchor.spec import HISTORICAL_ANCHOR_SEED_COHORT
from datp_core.experiments.registry import EXPERIMENTS, ExperimentDeclaration
from datp_core.runtime.configuration import DATA_ROOT


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


def executable_planning_evidence(experiment_id: ExperimentId) -> PlanningEvidence:
    return PlanningEvidence(
        experiment=experiment_id,
        disposition=PlanDisposition.EXECUTABLE,
        reason=PlanReason(
            "registered experiment recipe supplies locked execution prerequisites from protocol declarations"
        ),
    )


def _planning_evidence(declaration: ExperimentDeclaration) -> tuple[PlanningEvidence, ...]:
    evidence: list[PlanningEvidence] = []
    if declaration.readiness not in {
        ExperimentReadiness.SUPPRESSED,
        ExperimentReadiness.INFEASIBLE,
        ExperimentReadiness.BLOCKED,
    }:
        try:
            require_experiment_execution_ready(declaration.id)
        except UnresolvedScientificValueError as error:
            evidence.append(
                PlanningEvidence(
                    experiment=declaration.id,
                    disposition=PlanDisposition.BLOCKED,
                    reason=PlanReason(str(error)),
                )
            )
        else:
            evidence.append(executable_planning_evidence(declaration.id))
    return tuple(evidence)


def _plan_for_declaration(declaration: ExperimentDeclaration) -> ExperimentPlan:
    if declaration.id is ExperimentId.HISTORICAL_DATP_REPRODUCTION:
        return expand_experiment_plan(
            declarations=(declaration,),
            seed_cohort=HISTORICAL_ANCHOR_SEED_COHORT,
            evidence=(
                PlanningEvidence(
                    experiment=declaration.id,
                    disposition=PlanDisposition.EXECUTABLE,
                    reason=PlanReason("historical anchor reproduction uses the locked historical seed cohort"),
                ),
            ),
        )
    return expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=_seed_cohort_for(declaration.id),
        evidence=_planning_evidence(declaration),
    )


def build_programme_plan(experiment_id: ExperimentId | None) -> PlanPresentation:
    validation = validate_programme(experiment_id)
    declarations = EXPERIMENTS if experiment_id is None else (require_experiment_declaration(experiment_id),)
    plan = merge_experiment_plans(tuple(_plan_for_declaration(declaration) for declaration in declarations))
    experiment_ids = tuple(declaration.id for declaration in declarations)
    cohorts = tuple(
        (
            declaration.id,
            HISTORICAL_ANCHOR_SEED_COHORT.values
            if declaration.id is ExperimentId.HISTORICAL_DATP_REPRODUCTION
            else _seed_cohort_for(declaration.id).values,
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


def format_plan(
    presentation: PlanPresentation,
) -> DetailText:
    lines = [
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
    return DetailText("\n".join(lines))
