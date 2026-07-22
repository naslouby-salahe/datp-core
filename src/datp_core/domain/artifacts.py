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
    SPLIT_MANIFEST = "split_manifest"
    PARTITION_MANIFEST = "partition_manifest"
    DATASET_READINESS = "dataset_readiness"
    PREPROCESSING_EVIDENCE = "preprocessing_evidence"
    MODEL_CHECKPOINT = "model_checkpoint"
    PERSONALIZED_MODEL_CHECKPOINT = "personalized_model_checkpoint"
    CHECKPOINT_SELECTION = "checkpoint_selection"
    CALIBRATION_SCORES = "calibration_scores"
    FUTURE_RECALIBRATION_SCORES = "future_recalibration_scores"
    CALIBRATION_SUBSET = "calibration_subset"
    TEST_SCORES = "test_scores"
    THRESHOLDS = "thresholds"
    THRESHOLD_DIAGNOSTICS = "threshold_diagnostics"
    CLIENT_METRICS = "client_metrics"
    STATISTICAL_SUMMARY = "statistical_summary"
    RESULT_FREEZE = "result_freeze"
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

    def read(self, relative_path: str) -> ArtifactLookupResult: ...

    def inspect(self, relative_path: str) -> ArtifactLookupResult: ...

    def assess_reuse(
        self,
        relative_path: str,
        artifact_key: ArtifactKey,
        scientific_fingerprint: Fingerprint,
        execution_fingerprint: Fingerprint,
    ) -> ArtifactReuseDecision: ...
