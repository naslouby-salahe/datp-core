"""Atomic transaction execution: path validation, lock acquisition, staging, payload
materialization, checksums, manifest construction, atomic replacement, and filesystem
synchronization.

One private engine owns the complete lifecycle for both byte-payload and staged-file commits;
the only parameterized behavior is payload materialization and checksum computation.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock

from datp_core.artifacts.codecs.manifest import encode_manifest
from datp_core.artifacts.identity import ArtifactState
from datp_core.artifacts.lineage import validate_parent_lineage
from datp_core.artifacts.manifest import ArtifactManifest
from datp_core.artifacts.payloads import ArtifactCommitRequest, BytesPayload, FilePayload
from datp_core.artifacts.repository.models import ArtifactCommitResult
from datp_core.core.hashing import compute_file_checksum, compute_payload_checksum


def execute_atomic_transaction(
    request: ArtifactCommitRequest,
    outputs_dir: Path,
    lock_timeout: float,
) -> ArtifactCommitResult:
    """Private transaction engine: owns every lifecycle step exactly once.

    Every step other than payload materialization and checksum computation -- validation,
    locking, manifest construction, atomic replace, parent fsync -- is identical for both
    payload variants.
    """
    metadata = request.metadata

    lineage_error = validate_parent_lineage(metadata.artifact_key, metadata.parents)
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
                if resolved_source is None:
                    raise RuntimeError("Staged file payload was not validated before transaction execution")
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
