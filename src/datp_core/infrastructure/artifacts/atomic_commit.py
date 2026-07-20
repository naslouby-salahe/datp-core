"""Inter-process atomic artifact directory commit repository transactions backed by filelock."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock

from datp_core.domain.artifacts import (
    ArtifactCommitRequest,
    ArtifactCommitResult,
    ArtifactCompatibilityResult,
    ArtifactCorruptionReason,
    ArtifactFileCommitRequest,
    ArtifactFormat,
    ArtifactKey,
    ArtifactKind,
    ArtifactLookupResult,
    ArtifactManifest,
    ArtifactParent,
    ArtifactRepository,
    ArtifactReuseDecision,
    ArtifactState,
)
from datp_core.domain.fingerprints import Checksum, Fingerprint, compute_file_checksum, compute_payload_checksum
from datp_core.domain.identifiers import ArtifactId, ExperimentId
from datp_core.domain.values import Seed


def commit_artifact_atomically(
    request: ArtifactCommitRequest,
    outputs_dir: Path,
    lock_timeout: float,
) -> ArtifactCommitResult:
    """Commit payload bytes and manifest atomically inside a filelock-protected transaction."""
    relative_path = Path(request.relative_path)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return ArtifactCommitResult(success=False, error_message="Artifact relative path escapes the repository")
    target_dir = outputs_dir / relative_path

    lock_file = outputs_dir / f"{request.relative_path}.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)

    with FileLock(str(lock_file), timeout=lock_timeout):
        if target_dir.exists():
            return ArtifactCommitResult(
                success=False,
                error_message=f"Frozen artifact already exists at {target_dir}",
            )
        with TemporaryDirectory(dir=outputs_dir, prefix=".tmp_commit_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            payload_path = tmp_dir / f"payload.{request.artifact_format.value}"

            with open(payload_path, "wb") as f:
                f.write(request.payload_bytes)
                f.flush()
                os.fsync(f.fileno())

            checksum = compute_payload_checksum(request.payload_bytes)
            manifest = ArtifactManifest(
                artifact_key=request.artifact_key,
                artifact_format=request.artifact_format,
                state=ArtifactState.FROZEN,
                relative_path=request.relative_path,
                scientific_fingerprint=request.scientific_fingerprint,
                execution_fingerprint=request.execution_fingerprint,
                payload_checksum=checksum,
                schema_version=request.schema_version,
                parents=request.parents,
                creation_timestamp=request.creation_timestamp,
                environment_identity=request.environment_identity,
                experiment_id=request.experiment_id,
                seed=request.seed,
                is_frozen=True,
            )

            manifest_json = {
                "artifact_id": manifest.artifact_key.artifact_id.value,
                "artifact_kind": manifest.artifact_key.kind.value,
                "artifact_format": manifest.artifact_format.value,
                "scientific_fingerprint": manifest.scientific_fingerprint.value,
                "execution_fingerprint": manifest.execution_fingerprint.value,
                "payload_checksum": manifest.payload_checksum.value,
                "relative_path": manifest.relative_path,
                "state": manifest.state.value,
                "schema_version": manifest.schema_version,
                "parents": [
                    {
                        "artifact_id": parent.parent_key.artifact_id.value,
                        "artifact_kind": parent.parent_key.kind.value,
                        "scientific_fingerprint": parent.scientific_fingerprint.value,
                    }
                    for parent in manifest.parents
                ],
                "creation_timestamp": manifest.creation_timestamp,
                "environment_identity": manifest.environment_identity,
                "experiment_id": manifest.experiment_id.value if manifest.experiment_id else None,
                "seed": manifest.seed.value if manifest.seed else None,
                "is_frozen": manifest.is_frozen,
            }
            manifest_path = tmp_dir / "manifest.json"
            with open(manifest_path, "w", encoding="utf-8") as f:
                json.dump(manifest_json, f, indent=2)
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


def commit_artifact_file_atomically(
    request: ArtifactFileCommitRequest,
    outputs_dir: Path,
    lock_timeout: float,
) -> ArtifactCommitResult:
    """Copy a staged file into one atomic artifact transaction without reading it into memory."""
    source_file = Path(request.source_file).resolve()
    relative_path = Path(request.relative_path)
    if not source_file.is_file():
        return ArtifactCommitResult(success=False, error_message="Staged artifact source file is missing")
    if relative_path.is_absolute() or ".." in relative_path.parts:
        return ArtifactCommitResult(success=False, error_message="Artifact relative path escapes the repository")
    target_dir = outputs_dir / relative_path
    lock_file = outputs_dir / f"{request.relative_path}.lock"
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    with FileLock(str(lock_file), timeout=lock_timeout):
        if target_dir.exists():
            return ArtifactCommitResult(success=False, error_message=f"Frozen artifact already exists at {target_dir}")
        with TemporaryDirectory(dir=outputs_dir, prefix=".tmp_commit_") as tmp_dir_str:
            tmp_dir = Path(tmp_dir_str)
            payload_path = tmp_dir / f"payload.{request.artifact_format.value}"
            with source_file.open("rb") as source, payload_path.open("wb") as target:
                shutil.copyfileobj(source, target, length=1_048_576)
                target.flush()
                os.fsync(target.fileno())
            checksum = compute_file_checksum(payload_path)
            manifest = ArtifactManifest(
                artifact_key=request.artifact_key,
                artifact_format=request.artifact_format,
                state=ArtifactState.FROZEN,
                relative_path=request.relative_path,
                scientific_fingerprint=request.scientific_fingerprint,
                execution_fingerprint=request.execution_fingerprint,
                payload_checksum=checksum,
                schema_version=request.schema_version,
                parents=request.parents,
                creation_timestamp=request.creation_timestamp,
                environment_identity=request.environment_identity,
                experiment_id=request.experiment_id,
                seed=request.seed,
                is_frozen=True,
            )
            manifest_path = tmp_dir / "manifest.json"
            manifest_json = json.dumps(
                {
                    "artifact_id": manifest.artifact_key.artifact_id.value,
                    "artifact_kind": manifest.artifact_key.kind.value,
                    "artifact_format": manifest.artifact_format.value,
                    "scientific_fingerprint": manifest.scientific_fingerprint.value,
                    "execution_fingerprint": manifest.execution_fingerprint.value,
                    "payload_checksum": manifest.payload_checksum.value,
                    "relative_path": manifest.relative_path,
                    "state": manifest.state.value,
                    "schema_version": manifest.schema_version,
                    "parents": [
                        {
                            "artifact_id": parent.parent_key.artifact_id.value,
                            "artifact_kind": parent.parent_key.kind.value,
                            "scientific_fingerprint": parent.scientific_fingerprint.value,
                        }
                        for parent in manifest.parents
                    ],
                    "creation_timestamp": manifest.creation_timestamp,
                    "environment_identity": manifest.environment_identity,
                    "experiment_id": manifest.experiment_id.value if manifest.experiment_id else None,
                    "seed": manifest.seed.value if manifest.seed else None,
                    "is_frozen": True,
                },
                indent=2,
            )
            with manifest_path.open("w", encoding="utf-8") as manifest_file:
                manifest_file.write(manifest_json)
                manifest_file.flush()
                os.fsync(manifest_file.fileno())
            target_dir.parent.mkdir(parents=True, exist_ok=True)
            os.replace(tmp_dir, target_dir)
            parent_fd = os.open(target_dir.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
    return ArtifactCommitResult(success=True, manifest=manifest)


def inspect_committed_artifact(relative_path: str, outputs_dir: Path) -> ArtifactLookupResult:
    """Stream-verify a committed artifact without loading its payload into memory."""
    target_dir = outputs_dir / relative_path
    manifest_path = target_dir / "manifest.json"
    if not manifest_path.exists():
        return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.MANIFEST_MISSING)
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        artifact_format = ArtifactFormat(data["artifact_format"])
        payload_path = target_dir / f"payload.{artifact_format.value}"
        if not payload_path.exists():
            return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.PAYLOAD_MISSING)
        checksum = Checksum(data["payload_checksum"])
        if compute_file_checksum(payload_path) != checksum:
            return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.CHECKSUM_MISMATCH)
        parent_values = data["parents"]
        if not isinstance(parent_values, list):
            raise TypeError("parents must be a list")
        parents = tuple(
            ArtifactParent(
                parent_key=ArtifactKey(
                    artifact_id=ArtifactId(parent["artifact_id"]),
                    kind=ArtifactKind(parent["artifact_kind"]),
                ),
                scientific_fingerprint=Fingerprint(parent["scientific_fingerprint"]),
            )
            for parent in parent_values
            if isinstance(parent, dict)
        )
        if len(parents) != len(parent_values):
            raise TypeError("parents contains a non-mapping value")
        experiment_value = data["experiment_id"]
        seed_value = data["seed"]
        manifest = ArtifactManifest(
            artifact_key=ArtifactKey(
                artifact_id=ArtifactId(data["artifact_id"]),
                kind=ArtifactKind(data["artifact_kind"]),
            ),
            artifact_format=artifact_format,
            state=ArtifactState(data["state"]),
            relative_path=data["relative_path"],
            scientific_fingerprint=Fingerprint(data["scientific_fingerprint"]),
            execution_fingerprint=Fingerprint(data["execution_fingerprint"]),
            payload_checksum=checksum,
            schema_version=int(data["schema_version"]),
            parents=parents,
            creation_timestamp=float(data["creation_timestamp"]),
            environment_identity=str(data["environment_identity"]),
            experiment_id=ExperimentId(experiment_value) if isinstance(experiment_value, str) else None,
            seed=Seed(seed_value) if isinstance(seed_value, int) and not isinstance(seed_value, bool) else None,
            is_frozen=bool(data["is_frozen"]),
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return ArtifactLookupResult(found=False, corruption_reason=ArtifactCorruptionReason.MANIFEST_MISSING)
    return ArtifactLookupResult(found=True, manifest=manifest)


def read_committed_artifact(relative_path: str, outputs_dir: Path) -> ArtifactLookupResult:
    """Read a verified artifact payload for consumers that explicitly need its bytes."""
    inspection = inspect_committed_artifact(relative_path, outputs_dir)
    if not inspection.found or inspection.manifest is None:
        return inspection
    payload_path = outputs_dir / relative_path / f"payload.{inspection.manifest.artifact_format.value}"
    return ArtifactLookupResult(found=True, manifest=inspection.manifest, payload_bytes=payload_path.read_bytes())


class AtomicArtifactRepository(ArtifactRepository):
    """Filesystem implementation of the one immutable artifact repository port."""

    def __init__(self, outputs_dir: Path, lock_timeout: float) -> None:
        self._outputs_dir = outputs_dir
        self._lock_timeout = lock_timeout

    def commit(self, request: ArtifactCommitRequest) -> ArtifactCommitResult:
        return commit_artifact_atomically(request, self._outputs_dir, self._lock_timeout)

    def commit_file(self, request: ArtifactFileCommitRequest) -> ArtifactCommitResult:
        return commit_artifact_file_atomically(request, self._outputs_dir, self._lock_timeout)

    def read(self, relative_path: str) -> ArtifactLookupResult:
        return read_committed_artifact(relative_path, self._outputs_dir)

    def inspect(self, relative_path: str) -> ArtifactLookupResult:
        return inspect_committed_artifact(relative_path, self._outputs_dir)

    def assess_reuse(
        self,
        relative_path: str,
        artifact_key: ArtifactKey,
        scientific_fingerprint: Fingerprint,
        execution_fingerprint: Fingerprint,
    ) -> ArtifactReuseDecision:
        result = self.inspect(relative_path)
        if not result.found or result.manifest is None:
            return ArtifactReuseDecision(can_reuse=False, reason="artifact_not_committed")
        compatibility = _compatibility(result.manifest, artifact_key, scientific_fingerprint, execution_fingerprint)
        return ArtifactReuseDecision(
            can_reuse=compatibility.compatible,
            reason="compatible_frozen_artifact" if compatibility.compatible else ";".join(compatibility.reasons),
            existing_manifest=result.manifest,
        )


def _compatibility(
    manifest: ArtifactManifest,
    artifact_key: ArtifactKey,
    scientific_fingerprint: Fingerprint,
    execution_fingerprint: Fingerprint,
) -> ArtifactCompatibilityResult:
    reasons: list[str] = []
    if manifest.state is not ArtifactState.FROZEN or not manifest.is_frozen:
        reasons.append("artifact_not_frozen")
    if manifest.artifact_key != artifact_key:
        reasons.append("artifact_key_mismatch")
    if manifest.scientific_fingerprint != scientific_fingerprint:
        reasons.append("scientific_fingerprint_mismatch")
    if manifest.execution_fingerprint != execution_fingerprint:
        reasons.append("execution_fingerprint_mismatch")
    return ArtifactCompatibilityResult(compatible=not reasons, reasons=tuple(reasons))
