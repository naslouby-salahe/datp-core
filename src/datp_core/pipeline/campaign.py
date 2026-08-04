"""Deterministic campaign construction over executable experiment plans."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b

from datp_core.pipeline.planning import ExperimentCoordinate, ExperimentPlan, PlanDisposition


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
    digest: str

    def __post_init__(self) -> None:
        if tuple(item.ordinal for item in self.entries) != tuple(range(len(self.entries))):
            raise ValueError("campaign entries must use contiguous deterministic ordinals")
        if self.digest != _campaign_digest(self.entries):
            raise ValueError("campaign digest does not match campaign entries")


def build_campaign(plan: ExperimentPlan) -> CampaignPlan:
    coordinates = tuple(
        entry.coordinate for entry in plan.entries if entry.disposition is PlanDisposition.EXECUTABLE
    )
    entries = tuple(CampaignEntry(ordinal=index, coordinate=coordinate) for index, coordinate in enumerate(coordinates))
    return CampaignPlan(entries=entries, digest=_campaign_digest(entries))


def _campaign_digest(entries: tuple[CampaignEntry, ...]) -> str:
    payload = "\n".join(f"{entry.ordinal}|{entry.coordinate.stable_key}" for entry in entries).encode("utf-8")
    return blake2b(payload, digest_size=32).hexdigest()
