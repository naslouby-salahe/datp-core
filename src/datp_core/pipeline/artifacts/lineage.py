"""Artifact parent lineage construction and verification."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactKey
from datp_core.artifacts.lineage import ArtifactParent
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.config.project import ResolvedProjectConfiguration
from datp_core.core.hashing import Checksum


def artifact_parents(
    config: ResolvedProjectConfiguration,
    artifacts: tuple[tuple[ArtifactKey, str], ...],
    source_inventory_fingerprint: Checksum | None = None,
) -> tuple[ArtifactParent, ...]:
    """Build typed parent references, one per ``(artifact_key, relative_path)`` pair.

    The relative path is mandatory: it is what makes lineage actually verifiable
    (``verify_parent_lineage`` resolves it to read the parent's own committed manifest) rather
    than a bare key with no resolvable location.
    """
    return tuple(
        ArtifactParent(
            parent_key=artifact_key,
            parent_relative_path=relative_path,
            scientific_fingerprint=config.scientific_fingerprint,
            execution_fingerprint=config.execution_fingerprint,
            source_inventory_fingerprint=source_inventory_fingerprint,
        )
        for artifact_key, relative_path in artifacts
    )


def verify_parent_lineage(repository: ArtifactRepository, parents: tuple[ArtifactParent, ...]) -> str | None:
    """Resolve and verify every declared parent against its own committed manifest.

    ``repository.inspect`` already confirms the manifest and payload both exist and that the
    payload's recomputed checksum matches the manifest's recorded checksum (rejecting a missing
    or corrupt parent); ``ArtifactState`` has exactly one member (``FROZEN``), so a manifest that
    inspects successfully is trivially complete. This adds the remaining checks: the parent's
    actual key, scientific fingerprint, execution fingerprint, and source fingerprint must match
    what the child declared when it was committed. Returns an error message, or ``None`` if every
    parent verifies.
    """
    for parent in parents:
        resolved = repository.inspect(parent.parent_relative_path)
        if not resolved.found or resolved.manifest is None:
            return (
                f"Parent artifact '{parent.parent_key}' at '{parent.parent_relative_path}' is missing or "
                f"corrupt ({resolved.corruption_reason})"
            )
        manifest = resolved.manifest
        if manifest.artifact_key != parent.parent_key:
            return (
                f"Parent artifact key mismatch at '{parent.parent_relative_path}': expected "
                f"'{parent.parent_key}', found '{manifest.artifact_key}'"
            )
        if manifest.scientific_fingerprint != parent.scientific_fingerprint:
            return f"Parent artifact '{parent.parent_key}' has a mismatched scientific fingerprint"
        if manifest.execution_fingerprint != parent.execution_fingerprint:
            return f"Parent artifact '{parent.parent_key}' has a mismatched execution fingerprint"
        if (
            parent.source_inventory_fingerprint is not None
            and manifest.source_inventory_fingerprint is not None
            and manifest.source_inventory_fingerprint != parent.source_inventory_fingerprint
        ):
            return f"Parent artifact '{parent.parent_key}' has a mismatched source-inventory fingerprint"
    return None
