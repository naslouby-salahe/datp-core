"""Inter-process atomic artifact directory commit repository transactions backed by filelock.

One private transaction engine owns the complete lifecycle for both byte-payload and
staged-file commits. The public entry points are thin delegates with zero duplicated logic.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock

from datp_core.artifacts.models import (
    ArtifactCommitRequest,
    ArtifactCommitResult,
    ArtifactCompatibilityResult,
    ArtifactCorruptionReason,
    ArtifactKey,
    ArtifactLookupResult,
    ArtifactManifest,
    ArtifactParent,
    ArtifactRepository,
    ArtifactReuseDecision,
    ArtifactReuseReason,
    ArtifactState,
    BytesPayload,
    FilePayload,
)
from datp_core.artifacts.serialization import (
    ManifestDecodeError,
    ManifestSchemaIncompatibleError,
    decode_manifest,
    encode_manifest,
)
from datp_core.pipeline.fingerprints import Fingerprint, compute_file_checksum, compute_payload_checksum


def _validate_parent_lineage(artifact_key: ArtifactKey, parents: tuple[ArtifactParent, ...]) -> str | None:
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


def _execute_atomic_transaction(
    request: ArtifactCommitRequest,
    outputs_dir: Path,
    lock_timeout: float,
) -> ArtifactCommitResult:
    """Private transaction engine: owns every lifecycle step exactly once.

    The only parameterized behavior is payload materialization and checksum computation.
    Every other step — validation, locking, manifest construction, atomic replace, parent
    fsync — is identical for both payload variants.
    """
    metadata = request.metadata

    lineage_error = _validate_parent_lineage(metadata.artifact_key, metadata.parents)
    if lineage_error is not None:
        return ArtifactCommitResult(success=False, error_message=lineage_error)

    relative_path = Path(metadata.relative_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return ArtifactCommitResult(success=False, error_message="Artifact relative path escapes the repository")

    resolved_source: Path | None = None
    if isinstance(request.payload, FilePayload):
        resolved_source = Path(request.payload.source_file).resolve()
        if not resolved_source.is_file():
            return ArtifactCommitResult(success=False, error_message="Staged artifact source file is missing")

    target_dir = outputs_dir / metadata.relative_path
    lock_file = outputs_dir / f"{metadata.relative_path}.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    with FileLock(str(lock_file), timeout=lock_timeout):
        if target_dir.exists():
            return ArtifactCommitResult(
                success=False,
                error_message=f"Frozen artifact already exists at {target_dir}",
            )

        with TemporaryDirectory(dir=outputs_dir, prefix=".tmp_commit_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            payload_path = tmp_dir / f"payload.{metadata.artifact_format.value}"

            if isinstance(request.payload, BytesPayload):
                with open(payload_path, "wb") as f:
                    f.write(request.payload.payload_bytes)
                    f.flush()
                    os.fsync(f.fileno())
                checksum = compute_payload_checksum(request.payload.payload_bytes)
            else:
                # FilePayload — resolved_source guaranteed non-None by pre-lock validation
                assert resolved_source is not None
                with resolved_source.open("rb") as source, payload_path.open("wb") as target:
                    shutil.copyfileobj(source, target, length=1_048_576)
                    target.flush()
                    os.fsync(target.fileno())
                checksum = compute_file_checksum(payload_path)

            manifest = ArtifactManifest(
                artifact_key=metadata.artifact_key,
                artifact_format=metadata.artifact_format,
                state=ArtifactState.FROZEN,
                relative_path=metadata.relative_path,
                scientific_fingerprint=metadata.scientific_fingerprint,
                execution_fingerprint=metadata.execution_fingerprint,
                payload_checksum=checksum,
                schema_version=metadata.schema_version,
                parents=metadata.parents,
                creation_timestamp=metadata.creation_timestamp,
                environment_identity=metadata.environment_identity,
                experiment_id=metadata.experiment_id,
                seed=metadata.seed,
            )

            manifest_path = tmp_dir / "manifest.json"
            with open(manifest_path, "wb") as f:
                f.write(encode_manifest(manifest))
                f.flush()
                os.fsync(f.fileno())

            target_dir.parent.mkdir(parents=True, exist_ok=True)
            os.replace(tmp_dir, target_dir)
            parent_fd = os.open(target_dir.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)

    return ArtifactCommitResult(success=True, manifest=manifest)


class AtomicArtifactRepository(ArtifactRepository):
    """Filesystem implementation of the one immutable artifact repository port."""

    def __init__(self, outputs_dir: Path, lock_timeout: float) -> None:
        self._outputs_dir = outputs_dir
        self._lock_timeout = lock_timeout

    def commit(self, request: ArtifactCommitRequest) -> ArtifactCommitResult:
        return _execute_atomic_transaction(request, self._outputs_dir, self._lock_timeout)

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

    def assess_reuse(
        self,
        relative_path: str,
        artifact_key: ArtifactKey,
        scientific_fingerprint: Fingerprint,
        execution_fingerprint: Fingerprint,
    ) -> ArtifactReuseDecision:
        result = self.inspect(relative_path)
        if not result.found or result.manifest is None:
            return ArtifactReuseDecision(can_reuse=False, reason=(ArtifactReuseReason.ARTIFACT_NOT_COMMITTED,))
        compatibility = _compatibility(result.manifest, artifact_key, scientific_fingerprint, execution_fingerprint)
        return ArtifactReuseDecision(
            can_reuse=compatibility.compatible,
            reason=(
                (ArtifactReuseReason.COMPATIBLE_FROZEN_ARTIFACT,) if compatibility.compatible else compatibility.reasons
            ),
            existing_manifest=result.manifest,
        )


def _compatibility(
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


__all__ = ["AtomicArtifactRepository"]
