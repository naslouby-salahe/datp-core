"""Lineage-bearing immutable artifact contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from ..kernel.fingerprints import Fingerprint
from ..kernel.ids import ArtifactId
from ..kernel.values import PositiveInt


class ArtifactKind(StrEnum):
    RESOLVED_CONFIGURATION = "resolved_configuration"
    DATASET_READINESS = "dataset_readiness"
    MATERIALIZED_POPULATION = "materialized_population"
    TRAINING_STATE = "training_state"
    CHECKPOINT = "checkpoint"
    SCORE_SET = "score_set"
    THRESHOLD_SET = "threshold_set"
    METRIC_SET = "metric_set"
    STATISTICAL_RESULT = "statistical_result"
    REPORT = "report"
    RESULT_MANIFEST = "result_manifest"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactRef:
    artifact_id: ArtifactId
    kind: ArtifactKind


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactManifest:
    artifact_id: ArtifactId
    kind: ArtifactKind
    schema_version: PositiveInt
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    checksum: Fingerprint
    parents: tuple[ArtifactRef, ...]
    logical_scope: str
    completion_status: str
    created_at: datetime
    source_revision: str
    environment: tuple[tuple[str, str], ...]
    frozen: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class PendingArtifact:
    kind: ArtifactKind
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    parents: tuple[ArtifactRef, ...]
    logical_scope: str
    payload: bytes
    source_revision: str
    environment: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ReusableArtifact:
    ref: ArtifactRef


@dataclass(frozen=True, slots=True, kw_only=True)
class MissingArtifact:
    reason: str


@dataclass(frozen=True, slots=True, kw_only=True)
class InvalidArtifact:
    reason: str
