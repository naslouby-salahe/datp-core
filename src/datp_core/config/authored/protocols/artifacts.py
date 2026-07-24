"""Authored artifact-identity contract (protocols.yaml ``artifact_identity``)."""

from __future__ import annotations

from pydantic import ConfigDict, Field

from datp_core.config.authored.base import StrictFrozenConfigModel


class ArtifactFingerprintsConfig(StrictFrozenConfigModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True, populate_by_name=True)

    source: list[str]
    schema_stage: list[str] = Field(alias="schema")
    materialization: list[str]
    client_assignment: list[str]
    model_stage: list[str] = Field(alias="model")
    training: list[str]
    checkpoint: list[str]
    score: list[str]
    threshold: list[str]
    metric: list[str]
    analysis: list[str]


class ArtifactIdentityConfig(StrictFrozenConfigModel):
    hash_function: str
    digest_bytes: int
    canonical_serialization: str
    absolute_paths_excluded_from_identity: bool
    fingerprints: ArtifactFingerprintsConfig
    lineage_validation_before_reuse: list[str]
    reuse_rejected_when_any_changes: list[str]
