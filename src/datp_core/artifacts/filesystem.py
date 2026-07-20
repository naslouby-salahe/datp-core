"""Atomic, checksum-verified artifact storage; frozen artifacts cannot be overwritten."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from hashlib import blake2b
from json import dumps, loads
from pathlib import Path
from tempfile import mkdtemp

from ..kernel.fingerprints import Fingerprint
from ..kernel.ids import ArtifactId
from ..kernel.values import PositiveInt
from .domain import (
    ArtifactKind,
    ArtifactManifest,
    ArtifactRef,
    InvalidArtifact,
    MissingArtifact,
    PendingArtifact,
    ReusableArtifact,
)


class FilesystemArtifactStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def _directory(self, artifact_id: ArtifactId) -> Path:
        return self._root / artifact_id.value

    def commit(self, pending: PendingArtifact) -> ArtifactRef:
        checksum = Fingerprint("blake2b-256", blake2b(pending.payload, digest_size=32).hexdigest())
        artifact_id = ArtifactId(f"{pending.kind.value}-{pending.scientific_fingerprint.hexadecimal[:24]}")
        directory = self._directory(artifact_id)
        if directory.exists():
            decision = self.find(pending.kind, pending.scientific_fingerprint)
            if isinstance(decision, ReusableArtifact):
                return decision.ref
            raise FileExistsError(f"artifact location exists but is not reusable: {artifact_id}")
        directory.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(mkdtemp(dir=directory.parent, prefix=f".{artifact_id.value}-"))
        try:
            (temporary / "payload.bin").write_bytes(pending.payload)
            manifest = ArtifactManifest(
                artifact_id=artifact_id,
                kind=pending.kind,
                schema_version=PositiveInt(1),
                scientific_fingerprint=pending.scientific_fingerprint,
                execution_fingerprint=pending.execution_fingerprint,
                checksum=checksum,
                parents=pending.parents,
                logical_scope=pending.logical_scope,
                completion_status="completed",
                created_at=datetime.now(UTC),
                source_revision=pending.source_revision,
                environment=pending.environment,
                frozen=False,
            )
            (temporary / "manifest.json").write_text(_encode_manifest(manifest), encoding="utf-8")
            temporary.replace(directory)
            return ArtifactRef(artifact_id=artifact_id, kind=pending.kind)
        except BaseException:
            if temporary.exists():
                for child in temporary.iterdir():
                    child.unlink()
                temporary.rmdir()
            raise

    def find(
        self, kind: ArtifactKind, scientific_fingerprint: Fingerprint
    ) -> ReusableArtifact | MissingArtifact | InvalidArtifact:
        artifact_id = ArtifactId(f"{kind.value}-{scientific_fingerprint.hexadecimal[:24]}")
        directory = self._directory(artifact_id)
        if not directory.exists():
            return MissingArtifact(reason="artifact does not exist")
        try:
            manifest = self.read_manifest(ArtifactRef(artifact_id=artifact_id, kind=kind))
        except (OSError, ValueError, KeyError):
            return InvalidArtifact(reason="manifest is unreadable")
        if manifest.completion_status != "completed" or manifest.scientific_fingerprint != scientific_fingerprint:
            return InvalidArtifact(reason="manifest is incomplete or scientifically incompatible")
        payload = directory / "payload.bin"
        actual = blake2b(payload.read_bytes(), digest_size=32).hexdigest() if payload.is_file() else ""
        if actual != manifest.checksum.hexadecimal:
            return InvalidArtifact(reason="payload checksum mismatch")
        return ReusableArtifact(ref=ArtifactRef(artifact_id=artifact_id, kind=kind))

    def read_manifest(self, ref: ArtifactRef) -> ArtifactManifest:
        value = loads((self._directory(ref.artifact_id) / "manifest.json").read_text(encoding="utf-8"))
        parents = tuple(
            ArtifactRef(artifact_id=ArtifactId(parent["artifact_id"]), kind=ArtifactKind(parent["kind"]))
            for parent in value["parents"]
        )
        return ArtifactManifest(
            artifact_id=ArtifactId(value["artifact_id"]),
            kind=ArtifactKind(value["kind"]),
            schema_version=PositiveInt(value["schema_version"]),
            scientific_fingerprint=Fingerprint(**value["scientific_fingerprint"]),
            execution_fingerprint=Fingerprint(**value["execution_fingerprint"]),
            checksum=Fingerprint(**value["checksum"]),
            parents=parents,
            logical_scope=value["logical_scope"],
            completion_status=value["completion_status"],
            created_at=datetime.fromisoformat(value["created_at"]),
            source_revision=value["source_revision"],
            environment=tuple(tuple(item) for item in value["environment"]),
            frozen=bool(value["frozen"]),
        )


def _encode_manifest(manifest: ArtifactManifest) -> str:
    value = asdict(manifest)
    value["artifact_id"] = manifest.artifact_id.value
    value["kind"] = manifest.kind.value
    value["schema_version"] = manifest.schema_version.value
    value["created_at"] = manifest.created_at.isoformat()
    value["parents"] = [
        {"artifact_id": parent.artifact_id.value, "kind": parent.kind.value} for parent in manifest.parents
    ]
    return dumps(value, sort_keys=True, separators=(",", ":"), default=str)
