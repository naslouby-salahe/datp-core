"""Shared deterministic execution primitive for declared experiment families."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp_core.app.planning import ExperimentPlan, PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import FederatedThresholdMethod
from datp_core.experiments.common.coordinates import ExecutionRoute, execution_route_for
from datp_core.experiments.common.seeds import SeedCohort
from datp_core.experiments.execution.engine import CompletionRecordOutputStore, PipelineStageRunner, execute_campaign
from datp_core.experiments.execution.models import CampaignEntry, CampaignPlan, campaign_digest
from datp_core.experiments.registry import ExperimentDeclaration


@dataclass(frozen=True, slots=True, kw_only=True)
class DeclaredExperimentSeedResult:
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


def build_campaign(plan: ExperimentPlan) -> CampaignPlan:
    coordinates = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.disposition is PlanDisposition.EXECUTABLE
        and execution_route_for(entry.coordinate) is ExecutionRoute.SINGLE_COORDINATE
    )
    entries = tuple(CampaignEntry(ordinal=index, coordinate=coordinate) for index, coordinate in enumerate(coordinates))
    return CampaignPlan(entries=entries, digest=campaign_digest(entries), plan_digest=plan.digest)


def execute_declared_experiment_seed(
    *,
    declaration: ExperimentDeclaration,
    seed_cohort: SeedCohort,
    reason: str,
    output_root: Path,
    overwrite: bool,
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
    )


def execute_declared_campaign(
    *,
    campaign: CampaignPlan,
    declaration: ExperimentDeclaration,
    output_root: Path,
    overwrite: bool,
) -> DeclaredExperimentSeedResult:
    if not campaign.entries:
        raise ScientificContractError(
            ErrorMessage(f"{declaration.id.value} planning produced no executable coordinates"),
            subject=declaration.id,
        )
    execution = execute_campaign(
        campaign=campaign,
        stage_runner=PipelineStageRunner(),
        output_store=CompletionRecordOutputStore(),
        output_root=output_root,
        overwrite=overwrite,
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
        campaign_digest=campaign.digest,
        completed_threshold_methods=methods,
    )
