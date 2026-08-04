"""Typed experiment manifests binding plans, coordinates, and artifacts."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.pipeline.planning import ExperimentCoordinate
from datp_core.pipeline.publication.records import ArtifactRecord


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentManifest:
    coordinate: ExperimentCoordinate
    plan_digest: str
    campaign_digest: str
    protocol_digest: str
    artifacts: tuple[ArtifactRecord, ...]

    def __post_init__(self) -> None:
        if not self.plan_digest or not self.campaign_digest or not self.protocol_digest:
            raise ValueError("experiment manifests require plan, campaign, and protocol digests")
        paths = tuple(item.relative_path for item in self.artifacts)
        if len(paths) != len(frozenset(paths)):
            raise ValueError("experiment manifest artifact paths must be unique")
