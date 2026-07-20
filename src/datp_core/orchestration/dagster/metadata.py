"""Metadata conversion tools mapping DATP artifact lineage and fingerprints to Dagster metadata."""

from __future__ import annotations

from dagster import MetadataValue

from datp_core.domain.artifacts import ArtifactManifest


def build_dagster_metadata_from_manifest(manifest: ArtifactManifest) -> dict[str, MetadataValue]:
    """Convert DATP ArtifactManifest into Dagster MetadataValue dictionary."""
    return {
        "artifact_id": MetadataValue.text(manifest.artifact_key.artifact_id.value),
        "artifact_kind": MetadataValue.text(manifest.artifact_key.kind.value),
        "scientific_fingerprint": MetadataValue.text(manifest.scientific_fingerprint.value),
        "execution_fingerprint": MetadataValue.text(manifest.execution_fingerprint.value),
        "payload_checksum": MetadataValue.text(manifest.payload_checksum.value),
        "artifact_format": MetadataValue.text(manifest.artifact_format.value),
        "parent_count": MetadataValue.int(len(manifest.parents)),
    }
