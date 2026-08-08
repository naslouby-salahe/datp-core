"""Shared single-experiment campaign execution primitive.

Every registered experiment entry point plans one declared experiment for a
seed cohort, builds its executable campaign, executes it, checks for failures,
and reports which of the experiment's declared threshold methods actually
completed. This module owns that shape once so experiment modules keep only
their scientific logic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp_core.app.planning import PlanDisposition, PlanningEvidence, expand_experiment_plan
from datp_core.domain.enums import FederatedThresholdMethod
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.checksums import Checksum
from datp_core.pipeline.execution.engine import (
    CompletionRecordOutputStore,
    PipelineStageRunner,
    build_campaign,
    execute_campaign,
)
from datp_core.pipeline.execution.models import CampaignPlan
from datp_core.protocols.experiments import ExperimentDeclaration
from datp_core.protocols.seeds import SeedCohort


@dataclass(frozen=True, slots=True, kw_only=True)
class DeclaredExperimentSeedResult:
    campaign_digest: Checksum
    completed_threshold_methods: tuple[FederatedThresholdMethod, ...]


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
    campaign = build_campaign(plan)
    return execute_declared_campaign(
        campaign=campaign,
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
            f"{declaration.id.value} planning produced no executable coordinates",
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
            f"{declaration.id.value} execution did not complete: {blocked}",
            subject=declaration.id,
        )
    available_methods = frozenset(entry.coordinate.threshold_method for entry in campaign.entries)
    methods = tuple(method for method in declaration.federated_thresholds if method in available_methods)
    return DeclaredExperimentSeedResult(
        campaign_digest=campaign.digest,
        completed_threshold_methods=methods,
    )
