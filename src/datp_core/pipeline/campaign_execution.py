"""Deterministic campaign planning and canonical coordinate execution."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.domain.provenance import canonical_checksum
from datp_core.domain.values import Checksum, checksum_text
from datp_core.pipeline.execution import (
    ExecutionProvenance,
    ExperimentExecution,
    ExperimentOutputStore,
    StageRunner,
    execute_experiment,
)
from datp_core.pipeline.planning import (
    ExecutionRoute,
    ExperimentCoordinate,
    ExperimentPlan,
    PlanDisposition,
    execution_route_for,
)
from datp_core.protocols.experiments import EXPERIMENTS


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignEntry:
    ordinal: int
    coordinate: ExperimentCoordinate

    def __post_init__(self) -> None:
        if self.ordinal < 0:
            raise ValueError("campaign ordinals must be non-negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignPlan:
    entries: tuple[CampaignEntry, ...]
    digest: Checksum
    plan_digest: Checksum

    def __post_init__(self) -> None:
        if tuple(item.ordinal for item in self.entries) != tuple(range(len(self.entries))):
            raise ValueError("campaign entries must use contiguous deterministic ordinals")
        if self.digest != campaign_digest(self.entries):
            raise ValueError("campaign digest does not match campaign entries")


@dataclass(frozen=True, slots=True, kw_only=True)
class CampaignExecution:
    campaign_digest: Checksum
    experiments: tuple[ExperimentExecution, ...]


def build_campaign(plan: ExperimentPlan) -> CampaignPlan:
    coordinates = tuple(
        entry.coordinate
        for entry in plan.entries
        if entry.disposition is PlanDisposition.EXECUTABLE
        and execution_route_for(entry.coordinate) is ExecutionRoute.SINGLE_COORDINATE
    )
    entries = tuple(CampaignEntry(ordinal=index, coordinate=coordinate) for index, coordinate in enumerate(coordinates))
    return CampaignPlan(
        entries=entries,
        digest=campaign_digest(entries),
        plan_digest=Checksum(plan.digest),
    )


def protocol_digest() -> Checksum:
    return canonical_checksum(EXPERIMENTS)


def execute_campaign(
    *,
    campaign: CampaignPlan,
    stage_runner: StageRunner,
    output_store: ExperimentOutputStore,
    output_root,
) -> CampaignExecution:
    provenance = ExecutionProvenance(
        plan_digest=campaign.plan_digest,
        campaign_digest=campaign.digest,
        protocol_digest=protocol_digest(),
    )
    experiments = tuple(
        execute_experiment(
            coordinate=entry.coordinate,
            provenance=provenance,
            stage_runner=stage_runner,
            output_store=output_store,
            output_root=output_root,
        )
        for entry in campaign.entries
    )
    return CampaignExecution(campaign_digest=campaign.digest, experiments=experiments)


def campaign_digest(entries: tuple[CampaignEntry, ...]) -> Checksum:
    payload = "\n".join(f"{entry.ordinal}|{entry.coordinate.stable_key}" for entry in entries)
    return checksum_text(payload)
