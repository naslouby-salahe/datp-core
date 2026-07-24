"""Lookup and commit result records returned by the artifact repository."""

from __future__ import annotations

from attrs import define

from datp_core.artifacts.identity import ArtifactCorruptionReason
from datp_core.artifacts.manifest import ArtifactManifest


@define(frozen=True, slots=True, kw_only=True)
class ArtifactCommitResult:
    success: bool
    manifest: ArtifactManifest | None = None
    error_message: str | None = None


@define(frozen=True, slots=True, kw_only=True)
class ArtifactLookupResult:
    found: bool
    manifest: ArtifactManifest | None = None
    payload_bytes: bytes | None = None
    corruption_reason: ArtifactCorruptionReason | None = None
