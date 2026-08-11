from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp_core.app.planning import ExperimentPlan, PlanDisposition, PlanningEvidence, PlanReason, expand_experiment_plan
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import CoordinateStableKey, FederatedThresholdMethod
from datp_core.core.numeric import CampaignOrdinal
from datp_core.experiments.common.coordinates import ExecutionRoute, ExperimentCoordinate, execution_route_for
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution.engine import PipelineStageRunner, execute_campaign
from datp_core.experiments.execution.models import CampaignEntry, CampaignPlan, ProgressHook
from datp_core.experiments.registry import ExperimentDeclaration


@dataclass(frozen=True, slots=True, kw_only=True)
class DeclaredExperimentSeedResult:
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


def build_campaign(plan: ExperimentPlan) -> CampaignPlan:
    coordinates: list[ExperimentCoordinate] = []
    execution_keys: set[CoordinateStableKey] = set()
    for entry in plan.entries:
        coordinate = entry.coordinate
        if (
            entry.disposition is not PlanDisposition.EXECUTABLE
            or execution_route_for(coordinate) is not ExecutionRoute.SINGLE_COORDINATE
            or coordinate.execution_key in execution_keys
        ):
            continue
        execution_keys.add(coordinate.execution_key)
        coordinates.append(coordinate)
    entries = tuple(
        CampaignEntry(ordinal=CampaignOrdinal(index), coordinate=coordinate)
        for index, coordinate in enumerate(coordinates)
    )
    return CampaignPlan(entries=entries)


def execute_declared_experiment_seed(
    *,
    declaration: ExperimentDeclaration,
    seed_cohort: SeedCohort,
    reason: PlanReason,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> DeclaredExperimentSeedResult:
    plan = expand_experiment_plan(
        declarations=(declaration,),
        seed_cohort=seed_cohort,
        evidence=(PlanningEvidence(experiment=declaration.id, disposition=PlanDisposition.EXECUTABLE, reason=reason),),
    )
    return execute_declared_campaign(
        campaign=build_campaign(plan),
        declaration=declaration,
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )


def execute_declared_campaign(
    *,
    campaign: CampaignPlan,
    declaration: ExperimentDeclaration,
    output_root: Path,
    overwrite: bool,
    progress: ProgressHook | None = None,
) -> DeclaredExperimentSeedResult:
    if not campaign.entries:
        raise ScientificContractError(
            ErrorMessage(f"{declaration.id.value} planning produced no executable coordinates"),
            subject=declaration.id,
        )
    execution = execute_campaign(
        campaign=campaign,
        stage_runner=PipelineStageRunner(progress_hook=progress),
        output_root=output_root,
        overwrite=overwrite,
        progress=progress,
    )
    failed = tuple(result for result in execution.experiments if not result.successful)
    if failed:
        blocked = ", ".join(result.coordinate.stable_key for result in failed)
        raise ScientificContractError(
            ErrorMessage(f"{declaration.id.value} execution did not complete: {blocked}"),
            subject=declaration.id,
        )
    available_methods = frozenset(entry.coordinate.threshold_method for entry in campaign.entries)
    methods = tuple(method for method in declaration.federated_thresholds if method in available_methods)
    return DeclaredExperimentSeedResult(
        completed_threshold_methods=methods,
    )
