"""Immutable artifact manifest domain model.

Manifest JSON encoding/decoding lives in codecs/manifest.py, not here.
"""

from __future__ import annotations

from attrs import define

from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey, ArtifactState
from datp_core.artifacts.lineage import ArtifactParent
from datp_core.core.hashing import Checksum, Fingerprint
from datp_core.core.identifiers import ExperimentId
from datp_core.core.seeding import Seed


@define(frozen=True, slots=True, kw_only=True)
class ArtifactFingerprintsRecord:
    """Which upstream-stage fields feed each artifact-identity fingerprint (protocols.yaml)."""

    source: tuple[str, ...]
    schema_stage: tuple[str, ...]
    materialization: tuple[str, ...]
    client_assignment: tuple[str, ...]
    model_stage: tuple[str, ...]
    training: tuple[str, ...]
    checkpoint: tuple[str, ...]
    score: tuple[str, ...]
    threshold: tuple[str, ...]
    metric: tuple[str, ...]
    analysis: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ArtifactIdentityRecord:
    hash_function: str
    digest_bytes: int
    canonical_serialization: str
    absolute_paths_excluded_from_identity: bool
    fingerprints: ArtifactFingerprintsRecord
    lineage_validation_before_reuse: tuple[str, ...]
    reuse_rejected_when_any_changes: tuple[str, ...]


@define(frozen=True, slots=True, kw_only=True)
class ArtifactManifest:
    artifact_key: ArtifactKey
    artifact_format: ArtifactFormat
    state: ArtifactState
    relative_path: str
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    payload_checksum: Checksum
    schema_version: int
    parents: tuple[ArtifactParent, ...]
    creation_timestamp: float
    environment_identity: str
    experiment_id: ExperimentId | None = None
    seed: Seed | None = None
    source_inventory_fingerprint: Checksum | None = None
