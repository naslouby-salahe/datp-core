"""Frozen-artifact compatibility and reuse assessment."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactKey, ArtifactReuseReason
from datp_core.artifacts.manifest import ArtifactManifest
from datp_core.artifacts.repository.models import ArtifactCompatibilityResult
from datp_core.core.hashing import Checksum, Fingerprint


def assess_compatibility(
    manifest: ArtifactManifest,
    artifact_key: ArtifactKey,
    scientific_fingerprint: Fingerprint,
    execution_fingerprint: Fingerprint,
    source_inventory_fingerprint: Checksum | None = None,
) -> ArtifactCompatibilityResult:
    reasons: list[ArtifactReuseReason] = []
    if manifest.artifact_key != artifact_key:
        reasons.append(ArtifactReuseReason.KEY_MISMATCH)
    if manifest.scientific_fingerprint != scientific_fingerprint:
        reasons.append(ArtifactReuseReason.SCIENTIFIC_FINGERPRINT_MISMATCH)
    if manifest.execution_fingerprint != execution_fingerprint:
        reasons.append(ArtifactReuseReason.EXECUTION_FINGERPRINT_MISMATCH)
    if source_inventory_fingerprint is not None and (
        manifest.source_inventory_fingerprint is None
        or manifest.source_inventory_fingerprint != source_inventory_fingerprint
    ):
        reasons.append(ArtifactReuseReason.SOURCE_INVENTORY_FINGERPRINT_MISMATCH)
    return ArtifactCompatibilityResult(compatible=not reasons, reasons=tuple(reasons))
