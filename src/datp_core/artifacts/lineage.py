"""Artifact parent references and lineage validation, independent of filesystem transaction details."""

from __future__ import annotations

from attrs import define

from datp_core.artifacts.identity import ArtifactKey
from datp_core.core.hashing import Checksum, Fingerprint


@define(frozen=True, slots=True, kw_only=True)
class ArtifactParent:
    parent_key: ArtifactKey
    scientific_fingerprint: Fingerprint
    source_inventory_fingerprint: Checksum | None = None


def validate_parent_lineage(artifact_key: ArtifactKey, parents: tuple[ArtifactParent, ...]) -> str | None:
    """Reject self-referential and duplicate parent lineage declarations before any I/O.

    Full ancestor-existence and deep-cycle validation would require a key-to-path artifact
    index, which does not exist in Phase 1 (callers reference parents by key only, with no
    resolvable location) -- that is Phase 2/3 artifact-catalog scope. This bounded check still
    catches the direct, always-invalid cases representable with today's contract.
    """
    seen_keys: list[ArtifactKey] = []
    for parent in parents:
        if parent.parent_key == artifact_key:
            return f"Artifact '{artifact_key}' declares itself as its own parent"
        if parent.parent_key in seen_keys:
            return f"Artifact '{artifact_key}' declares duplicate parent lineage for '{parent.parent_key}'"
        seen_keys.append(parent.parent_key)
    return None
