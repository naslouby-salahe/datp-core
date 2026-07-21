"""Domain models for artifact identities, lifecycle states, formats, manifests, and repository transactions."""

from __future__ import annotations

from enum import Enum
from typing import Protocol, runtime_checkable

from attrs import define, field

from datp_core.domain.fingerprints import Checksum, Fingerprint
from datp_core.domain.identifiers import ArtifactId, ExperimentId
from datp_core.domain.values import Seed


class ArtifactKind(Enum):
    RESOLVED_CONFIG = "resolved_config"
    MATERIALIZED_DATASET = "materialized_dataset"
    MODEL_CHECKPOINT = "model_checkpoint"
    CALIBRATION_SCORES = "calibration_scores"
    TEST_SCORES = "test_scores"
    THRESHOLDS = "thresholds"
    CLIENT_METRICS = "client_metrics"
    STATISTICAL_SUMMARY = "statistical_summary"
    RESULT_REPORT = "result_report"
    REPORT = "report"


class ArtifactFormat(Enum):
    JSON = "json"
    PARQUET = "parquet"
    SAFETENSORS = "safetensors"
    TEXT = "text"


class ArtifactState(Enum):
    """The atomic commit transaction is all-or-nothing: no partial/pending state is ever
    reader-visible, so FROZEN is the only lifecycle state a committed manifest can carry."""

    FROZEN = "frozen"


class ArtifactCorruptionReason(Enum):
    CHECKSUM_MISMATCH = "checksum_mismatch"
    MANIFEST_MISSING = "manifest_missing"
    PAYLOAD_MISSING = "payload_missing"
    SCHEMA_INCOMPATIBLE = "schema_incompatible"


@define(frozen=True, slots=True, kw_only=True)
class ArtifactKey:
    artifact_id: ArtifactId
    kind: ArtifactKind

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.artifact_id.value}"


@define(frozen=True, slots=True, kw_only=True)
class ArtifactParent:
    parent_key: ArtifactKey
    scientific_fingerprint: Fingerprint


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
    is_frozen: bool
    experiment_id: ExperimentId | None = None
    seed: Seed | None = None


@define(frozen=True, slots=True, kw_only=True)
class ArtifactCommitRequest:
    artifact_key: ArtifactKey
    artifact_format: ArtifactFormat
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    payload_bytes: bytes
    relative_path: str
    parents: tuple[ArtifactParent, ...]
    schema_version: int
    creation_timestamp: float
    environment_identity: str
    experiment_id: ExperimentId | None = None
    seed: Seed | None = None


@define(frozen=True, slots=True, kw_only=True)
class ArtifactFileCommitRequest:
    """Artifact commit metadata for a staged payload file owned by the transaction."""

    artifact_key: ArtifactKey
    artifact_format: ArtifactFormat
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    source_file: str
    relative_path: str
    parents: tuple[ArtifactParent, ...]
    schema_version: int
    creation_timestamp: float
    environment_identity: str
    experiment_id: ExperimentId | None = None
    seed: Seed | None = None


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


@define(frozen=True, slots=True, kw_only=True)
class ArtifactReuseDecision:
    can_reuse: bool
    reason: str
    existing_manifest: ArtifactManifest | None = None


@define(frozen=True, slots=True, kw_only=True)
class ArtifactCompatibilityResult:
    compatible: bool
    reasons: tuple[str, ...] = field(factory=tuple)


@runtime_checkable
class ArtifactRepository(Protocol):
    """Single application-facing authority for immutable artifact persistence."""

    def commit(self, request: ArtifactCommitRequest) -> ArtifactCommitResult: ...

    def commit_file(self, request: ArtifactFileCommitRequest) -> ArtifactCommitResult: ...

    def read(self, relative_path: str) -> ArtifactLookupResult: ...

    def inspect(self, relative_path: str) -> ArtifactLookupResult: ...

    def assess_reuse(
        self,
        relative_path: str,
        artifact_key: ArtifactKey,
        scientific_fingerprint: Fingerprint,
        execution_fingerprint: Fingerprint,
    ) -> ArtifactReuseDecision: ...
