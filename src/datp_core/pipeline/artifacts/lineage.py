"""Artifact parent lineage construction."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactKey
from datp_core.artifacts.lineage import ArtifactParent
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.hashing import Checksum


def artifact_parents(
    config: ResolvedProjectConfiguration,
    artifacts: tuple[ArtifactKey, ...],
    source_inventory_fingerprint: Checksum | None = None,
) -> tuple[ArtifactParent, ...]:
    return tuple(
        ArtifactParent(
            parent_key=artifact,
            scientific_fingerprint=config.scientific_fingerprint,
            source_inventory_fingerprint=source_inventory_fingerprint,
        )
        for artifact in artifacts
    )
