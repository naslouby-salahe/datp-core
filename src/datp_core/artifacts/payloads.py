"""Artifact commit payload variants: byte payload, staged-file payload, commit metadata, and the
closed payload union consumed by the atomic commit transaction."""

from __future__ import annotations

from attrs import define

from datp_core.artifacts.identity import ArtifactFormat, ArtifactKey
from datp_core.artifacts.lineage import ArtifactParent
from datp_core.core.hashing import Fingerprint
from datp_core.core.identifiers import ExperimentId
from datp_core.core.seeding import Seed


@define(frozen=True, slots=True, kw_only=True)
class ArtifactCommitMetadata:
    """Shared immutable metadata for every artifact commit, regardless of payload source."""

    artifact_key: ArtifactKey
    artifact_format: ArtifactFormat
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    relative_path: str
    parents: tuple[ArtifactParent, ...]
    schema_version: int
    creation_timestamp: float
    environment_identity: str
    experiment_id: ExperimentId | None = None
    seed: Seed | None = None


@define(frozen=True, slots=True, kw_only=True)
class BytesPayload:
    """In-memory payload bytes for the artifact transaction."""

    payload_bytes: bytes


@define(frozen=True, slots=True, kw_only=True)
class FilePayload:
    """Staged-file path whose contents will be copied into the artifact transaction."""

    source_file: str


type ArtifactPayload = BytesPayload | FilePayload


@define(frozen=True, slots=True, kw_only=True)
class ArtifactCommitRequest:
    """One artifact commit request with shared metadata and a closed payload-source variant.

    The payload discriminates between in-memory bytes and a staged file on disk.
    Both variants flow through the same atomic transaction engine.
    """

    metadata: ArtifactCommitMetadata
    payload: ArtifactPayload
