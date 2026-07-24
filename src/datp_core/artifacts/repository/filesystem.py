"""Filesystem-backed artifact repository implementation.

Thin delegate: every transaction step lives in transaction.py.
"""

from __future__ import annotations

from pathlib import Path

from datp_core.artifacts.codecs.manifest import decode_manifest
from datp_core.artifacts.errors import ManifestDecodeError, ManifestSchemaIncompatibleError
from datp_core.artifacts.identity import ArtifactCorruptionReason
from datp_core.artifacts.payloads import ArtifactCommitRequest
from datp_core.artifacts.repository.models import ArtifactCommitResult, ArtifactLookupResult
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.artifacts.repository.transaction import execute_atomic_transaction
from datp_core.core.hashing import compute_file_checksum


class AtomicArtifactRepository(ArtifactRepository):
    """Filesystem implementation of the one immutable artifact repository port."""

    def __init__(self, outputs_dir: Path, lock_timeout: float) -> None:
        self._outputs_dir = outputs_dir
        self._lock_timeout = lock_timeout

    def commit(self, request: ArtifactCommitRequest) -> ArtifactCommitResult:
        return execute_atomic_transaction(request, self._outputs_dir, self._lock_timeout)

    def read(self, relative_path: str) -> ArtifactLookupResult:
        inspection = self.inspect(relative_path)
        if not inspection.found or inspection.manifest is None:
            return inspection
        payload_path = self._outputs_dir / relative_path / f"payload.{inspection.manifest.artifact_format.value}"
        return ArtifactLookupResult(found=True, manifest=inspection.manifest, payload_bytes=payload_path.read_bytes())

    def inspect(self, relative_path: str) -> ArtifactLookupResult:
        target_dir = self._outputs_dir / relative_path
        manifest_path = target_dir / "manifest.json"
        if not manifest_path.exists():
            return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.MANIFEST_MISSING)
        try:
            manifest = decode_manifest(manifest_path.read_bytes())
        except ManifestSchemaIncompatibleError:
            return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.SCHEMA_INCOMPATIBLE)
        except ManifestDecodeError:
            return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.MANIFEST_MISSING)
        payload_path = target_dir / f"payload.{manifest.artifact_format.value}"
        if not payload_path.exists():
            return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.PAYLOAD_MISSING)
        if compute_file_checksum(payload_path) != manifest.payload_checksum:
            return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.CHECKSUM_MISMATCH)
        return ArtifactLookupResult(found=True, manifest=manifest)


__all__ = ["AtomicArtifactRepository"]
