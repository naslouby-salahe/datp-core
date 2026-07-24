"""Artifact parent references and lineage validation, independent of filesystem transaction details."""

from __future__ import annotations

from attrs import define

from datp_core.artifacts.identity import ArtifactKey
from datp_core.core.hashing import Checksum, Fingerprint


@define(frozen=True, slots=True, kw_only=True)
class ArtifactParent:
    parent_key: ArtifactKey
    parent_relative_path: str
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    source_inventory_fingerprint: Checksum | None = None


def validate_parent_lineage(artifact_key: ArtifactKey, parents: tuple[ArtifactParent, ...]) -> str | None:
    """Reject self-referential and duplicate parent lineage declarations before any I/O.

    This is the cheap, I/O-free structural check run inside the atomic transaction itself. Real
    ancestor existence, checksum, and fingerprint verification -- which requires reading the
    parent's own committed manifest via ``parent_relative_path`` -- is
    ``pipeline.artifacts.lineage.verify_parent_lineage``, run by ``commit_artifact`` before every
    commit and before every reuse.
    """
    seen_keys: list[ArtifactKey] = []
    for parent in parents:
        if parent.parent_key == artifact_key:
            return f"Artifact '{artifact_key}' declares itself as its own parent"
        if parent.parent_key in seen_keys:
            return f"Artifact '{artifact_key}' declares duplicate parent lineage for '{parent.parent_key}'"
        seen_keys.append(parent.parent_key)
    return None
