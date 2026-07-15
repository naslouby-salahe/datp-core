from dataclasses import dataclass
from os import O_DIRECTORY, O_RDONLY, close, fsync, replace
from os import open as open_file
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import assert_never

import msgspec

from datp_core.application.ports.persistence import (
    ArtifactLookupRequest,
    ArtifactLookupResult,
    ArtifactValidationResult,
    ArtifactWriteResult,
    ValidateArtifactRequest,
    WriteArtifactRequest,
)
from datp_core.domain.artifacts.keys import ArtifactKey, WriteDisposition
from datp_core.domain.artifacts.lineage import IntegrityStatus, SchemaCompatibility
from datp_core.domain.artifacts.references import ArtifactRef, ValidationStatus
from datp_core.domain.errors import ArtifactError, PartialArtifactError
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash, blake3_file_content_hash
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
from datp_core.infrastructure.persistence.roots import BoundStorageRoot


@dataclass(frozen=True, slots=True, kw_only=True)
class FileArtifactStore:
    root: BoundStorageRoot

    def lookup(self, request: ArtifactLookupRequest) -> ArtifactLookupResult:
        manifest = self._read_manifest(request.artifact_id.value)
        if manifest is None:
            return ArtifactLookupResult(artifact=None)
        _verify_existing_content(path=self._location_for(request.key, manifest), artifact=manifest)
        return ArtifactLookupResult(artifact=manifest)

    def write_atomically(self, request: WriteArtifactRequest) -> ArtifactWriteResult:
        _verify_requested_content(request)
        existing = self._read_manifest(request.artifact.artifact_id.value)
        if existing is not None:
            _verify_existing_artifact(existing=existing, requested=request.artifact)
            return ArtifactWriteResult(artifact=existing)
        _validate_write_disposition(request)
        final_path = self._location_for(request.key, request.artifact)
        if final_path.exists():
            _verify_existing_content(path=final_path, artifact=request.artifact)
        else:
            self._write_verified_temp_and_replace(path=final_path, request=request)
        self._write_manifest(request.artifact)
        return ArtifactWriteResult(artifact=request.artifact)

    def validate_integrity(self, request: ValidateArtifactRequest) -> ArtifactValidationResult:
        stored = self._read_manifest(request.artifact.artifact_id.value)
        if stored is None:
            return _invalid_result(request.artifact, IntegrityStatus.MISSING, SchemaCompatibility.UNKNOWN)
        path = self._location_for(request.key, stored)
        if not path.exists():
            return _invalid_result(request.artifact, IntegrityStatus.MISSING, SchemaCompatibility.COMPATIBLE)
        try:
            content_hash = blake3_file_content_hash(path)
        except OSError as error:
            raise ArtifactError(
                detail="persisted artifact content is unavailable",
                artifact_id=request.artifact.artifact_id.value,
                stage="verify",
            ) from error
        if content_hash != stored.content_hash:
            return _invalid_result(request.artifact, IntegrityStatus.CORRUPT, SchemaCompatibility.COMPATIBLE)
        if stored.schema_version != request.artifact.schema_version:
            return _invalid_result(request.artifact, IntegrityStatus.INTACT, SchemaCompatibility.INCOMPATIBLE)
        if stored != request.artifact:
            return _invalid_result(request.artifact, IntegrityStatus.MISSING, SchemaCompatibility.UNKNOWN)
        return ArtifactValidationResult(
            artifact=request.artifact,
            status=ValidationStatus.VALID,
            integrity=IntegrityStatus.INTACT,
            schema_compatibility=SchemaCompatibility.COMPATIBLE,
        )

    def _location_for(self, key: ArtifactKey, artifact: ArtifactRef) -> Path:
        return (
            ArtifactPathResolver()
            .resolve(ResolveArtifactLocationRequest(key=key, root=self.root, artifact=artifact))
            .absolute_path
        )

    def _write_verified_temp_and_replace(self, *, path: Path, request: WriteArtifactRequest) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(dir=path.parent, prefix=".artifact-", delete=False) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(request.content)
                temporary_file.flush()
                fsync(temporary_file.fileno())
            _verify_existing_content(path=temporary_path, artifact=request.artifact)
            _verify_same_filesystem(
                temporary_path=temporary_path,
                destination=path.parent,
                artifact_id=request.artifact.artifact_id.value,
            )
            replace(temporary_path, path)
            _fsync_directory(path.parent)
        except OSError as error:
            raise PartialArtifactError(
                detail="atomic artifact write did not complete",
                artifact_id=request.artifact.artifact_id.value,
                stage="commit",
            ) from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _read_manifest(self, artifact_id: str) -> ArtifactRef | None:
        path = self.root.absolute_path / ".artifact-manifests" / artifact_id
        if not path.exists():
            return None
        try:
            return msgspec.json.decode(path.read_bytes(), type=ArtifactRef)
        except (OSError, msgspec.DecodeError, msgspec.ValidationError) as error:
            raise ArtifactError(
                detail="persisted artifact manifest is unreadable or invalid",
                artifact_id=artifact_id,
                stage="verify",
            ) from error

    def _write_manifest(self, artifact: ArtifactRef) -> None:
        path = self.root.absolute_path / ".artifact-manifests" / artifact.artifact_id.value
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(dir=path.parent, prefix=".manifest-", delete=False) as temporary_file:
                temporary_path = Path(temporary_file.name)
                temporary_file.write(msgspec.json.encode(artifact))
                temporary_file.flush()
                fsync(temporary_file.fileno())
            replace(temporary_path, path)
            _fsync_directory(path.parent)
        except OSError as error:
            raise PartialArtifactError(
                detail="artifact content committed but manifest update did not complete",
                artifact_id=artifact.artifact_id.value,
                stage="manifest",
            ) from error
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)


def _verify_requested_content(request: WriteArtifactRequest) -> None:
    if blake3_bytes_content_hash(request.content) != request.artifact.content_hash:
        raise ArtifactError(
            detail="requested content hash does not match artifact reference",
            artifact_id=request.artifact.artifact_id.value,
            stage="verify",
        )


def _validate_write_disposition(request: WriteArtifactRequest) -> None:
    match request.write_disposition:
        case WriteDisposition.CREATE_IF_ABSENT | WriteDisposition.ATOMIC_STAGE_COMMIT:
            return
        case WriteDisposition.VERIFY_OR_FAIL:
            raise ArtifactError(
                detail="verification requested for an artifact without a completed manifest",
                artifact_id=request.artifact.artifact_id.value,
                stage="verify",
            )
        case _ as unreachable:
            assert_never(unreachable)


def _verify_existing_artifact(*, existing: ArtifactRef, requested: ArtifactRef) -> None:
    if existing != requested:
        raise ArtifactError(
            detail="logical artifact id already has different immutable bytes or schema",
            artifact_id=requested.artifact_id.value,
            stage="verify",
        )


def _verify_existing_content(*, path: Path, artifact: ArtifactRef) -> None:
    try:
        content_hash = blake3_file_content_hash(path)
    except OSError as error:
        raise ArtifactError(
            detail="persisted artifact content is unavailable",
            artifact_id=artifact.artifact_id.value,
            stage="verify",
        ) from error
    if content_hash != artifact.content_hash:
        raise ArtifactError(
            detail="persisted content hash conflicts with artifact reference",
            artifact_id=artifact.artifact_id.value,
            stage="verify",
        )


def _verify_same_filesystem(*, temporary_path: Path, destination: Path, artifact_id: str) -> None:
    if temporary_path.stat().st_dev != destination.stat().st_dev:
        raise PartialArtifactError(
            detail="atomic artifact commit requires temporary and destination paths on one filesystem",
            artifact_id=artifact_id,
            stage="commit",
        )


def _fsync_directory(path: Path) -> None:
    descriptor = open_file(path, O_RDONLY | O_DIRECTORY)
    try:
        fsync(descriptor)
    finally:
        close(descriptor)


def _invalid_result(
    artifact: ArtifactRef, integrity: IntegrityStatus, schema: SchemaCompatibility
) -> ArtifactValidationResult:
    return ArtifactValidationResult(
        artifact=artifact, status=ValidationStatus.INVALID, integrity=integrity, schema_compatibility=schema
    )
