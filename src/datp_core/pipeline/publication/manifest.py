"""Typed experiment manifests binding plans, coordinates, protocols, and artifacts."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.domain.values import Checksum
from datp_core.pipeline.planning import ExperimentCoordinate
from datp_core.pipeline.publication.records import ArtifactRecord, ArtifactState


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentManifest:
    coordinate: ExperimentCoordinate
    plan_digest: Checksum
    campaign_digest: Checksum
    protocol_digest: Checksum
    artifacts: tuple[ArtifactRecord, ...]

    def __post_init__(self) -> None:
        if not self.artifacts:
            raise ValueError("experiment manifests require an artifact inventory")
        paths = tuple(item.relative_path for item in self.artifacts)
        if len(paths) != len(frozenset(paths)):
            raise ValueError("experiment manifest artifact paths must be unique")
        if any(item.state not in {ArtifactState.PUBLISHED, ArtifactState.REUSED} for item in self.artifacts):
            raise ValueError("experiment manifests cannot reference invalid or incomplete artifacts")
