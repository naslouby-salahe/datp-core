"""Artifact-family completion protocol — typed multi-artifact stage output atomicity.

When a pipeline stage produces multiple logically inseparable artifacts (e.g. a threshold
frame plus its diagnostics, or a materialized dataset plus its split manifest, readiness
report, and preprocessing evidence), the stage is only considered complete when every
required member has been committed and is verifiable.

This module provides:
* ``ArtifactFamilyMember`` — one required companion artifact.
* ``ArtifactFamilyCompletion`` — the full family definition.
* ``verify_family_completion`` — check every member exists and is valid before reuse.
"""

from __future__ import annotations

from attrs import define

from datp_core.artifacts.identity import ArtifactKey
from datp_core.artifacts.repository.port import ArtifactRepository
from datp_core.core.hashing import Checksum, Fingerprint


@define(frozen=True, slots=True, kw_only=True)
class ArtifactFamilyMember:
    """One required companion artifact within a stage-output family."""

    artifact_key: ArtifactKey
    relative_path: str


@define(frozen=True, slots=True, kw_only=True)
class ArtifactFamilyCompletion:
    """Typed definition of a complete artifact family for one stage invocation."""

    primary_key: ArtifactKey
    primary_relative_path: str
    members: tuple[ArtifactFamilyMember, ...]


def verify_family_completion(
    family: ArtifactFamilyCompletion,
    *,
    repository: ArtifactRepository,
    scientific_fingerprint: Fingerprint,
    execution_fingerprint: Fingerprint,
    source_inventory_fingerprint: Checksum | None = None,
) -> bool:
    """Return True when the primary artifact and every declared member exists and is compatible.

    A partially committed family (primary present but a member missing or incompatible) is
    never reported as reusable.
    """
    primary_reuse = repository.assess_reuse(
        family.primary_relative_path,
        family.primary_key,
        scientific_fingerprint,
        execution_fingerprint,
        source_inventory_fingerprint=source_inventory_fingerprint,
    )
    if not primary_reuse.can_reuse:
        return False
    for member in family.members:
        member_reuse = repository.assess_reuse(
            member.relative_path,
            member.artifact_key,
            scientific_fingerprint,
            execution_fingerprint,
            source_inventory_fingerprint=source_inventory_fingerprint,
        )
        if not member_reuse.can_reuse:
            return False
    return True
