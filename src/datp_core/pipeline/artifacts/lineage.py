"""Artifact parent lineage construction."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactKey
from datp_core.artifacts.lineage import ArtifactParent
from datp_core.config.project import ResolvedProjectConfiguration


def artifact_parents(
    config: ResolvedProjectConfiguration, artifacts: tuple[ArtifactKey, ...]
) -> tuple[ArtifactParent, ...]:
    return tuple(
        ArtifactParent(parent_key=artifact, scientific_fingerprint=config.scientific_fingerprint)
        for artifact in artifacts
    )
