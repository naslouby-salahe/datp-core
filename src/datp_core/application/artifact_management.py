"""Artifact management repository use case."""

from __future__ import annotations

from json import dumps, loads
from pathlib import Path

from datp_core.domain.artifacts import ArtifactFormat, ArtifactKey, ArtifactManifest, ArtifactState
from datp_core.domain.fingerprints import compute_fingerprint, compute_payload_checksum
from datp_core.infrastructure.artifacts.atomic_commit import atomic_write_file
from datp_core.infrastructure.artifacts.serializers import structure_manifest, unstructure_manifest


class ArtifactManagementUseCase:
    def __init__(self, root_dir: Path = Path("outputs")) -> None:
        self._root_dir = root_dir

    def commit_artifact(
        self,
        key: ArtifactKey,
        fmt: ArtifactFormat,
        payload: bytes,
        scientific_data: object,
    ) -> ArtifactManifest:
        rel_path = f"{key.kind.value}/{key.artifact_id.value}.{fmt.value}"
        target_path = self._root_dir / rel_path

        atomic_write_file(target_path, payload)

        sci_fp = compute_fingerprint(scientific_data)
        checksum = compute_payload_checksum(payload)

        manifest = ArtifactManifest(
            artifact_key=key,
            format=fmt,
            state=ArtifactState.COMMITTED,
            relative_path=rel_path,
            scientific_fingerprint=sci_fp,
            execution_fingerprint=sci_fp,
            payload_checksum=checksum,
        )

        manifest_data = unstructure_manifest(manifest)
        manifest_bytes = dumps(manifest_data, indent=2).encode("utf-8")
        manifest_path = self._root_dir / f"{key.kind.value}/{key.artifact_id.value}.manifest.json"
        atomic_write_file(manifest_path, manifest_bytes)

        return manifest

    def load_manifest(self, key: ArtifactKey) -> ArtifactManifest:
        manifest_path = self._root_dir / f"{key.kind.value}/{key.artifact_id.value}.manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found for artifact key: {key}")
        data = loads(manifest_path.read_text(encoding="utf-8"))
        return structure_manifest(data)
