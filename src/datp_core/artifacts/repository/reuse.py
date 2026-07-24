"""Frozen-artifact compatibility and reuse assessment."""

from __future__ import annotations

from datp_core.artifacts.identity import ArtifactKey, ArtifactReuseReason
from datp_core.artifacts.manifest import ArtifactManifest
from datp_core.artifacts.repository.models import ArtifactCompatibilityResult
from datp_core.core.hashing import Fingerprint


def assess_compatibility(
    manifest: ArtifactManifest,
    artifact_key: ArtifactKey,
    scientific_fingerprint: Fingerprint,
    execution_fingerprint: Fingerprint,
) -> ArtifactCompatibilityResult:
    reasons: list[ArtifactReuseReason] = []
    if manifest.artifact_key != artifact_key:
        reasons.append(ArtifactReuseReason.KEY_MISMATCH)
    if manifest.scientific_fingerprint != scientific_fingerprint:
        reasons.append(ArtifactReuseReason.SCIENTIFIC_FINGERPRINT_MISMATCH)
    if manifest.execution_fingerprint != execution_fingerprint:
        reasons.append(ArtifactReuseReason.EXECUTION_FINGERPRINT_MISMATCH)
    return ArtifactCompatibilityResult(compatible=not reasons, reasons=tuple(reasons))
