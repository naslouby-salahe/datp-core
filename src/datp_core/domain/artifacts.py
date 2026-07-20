"""Domain models for artifact identities, lifecycle states, formats, and manifests."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .fingerprints import Checksum, Fingerprint
from .identifiers import ArtifactId
from .values import Seed


class ArtifactKind(Enum):
    RESOLVED_CONFIG = "resolved_config"
    MATERIALIZED_DATASET = "materialized_dataset"
    MODEL_CHECKPOINT = "model_checkpoint"
    CALIBRATION_SCORES = "calibration_scores"
    TEST_SCORES = "test_scores"
    THRESHOLDS = "thresholds"
    CLIENT_METRICS = "client_metrics"
    STATISTICAL_RESULTS = "statistical_results"
    REPORT = "report"


class ArtifactFormat(Enum):
    JSON = "json"
    PARQUET = "parquet"
    SAFETENSORS = "safetensors"
    CSV = "csv"
    TEXT = "text"


class ArtifactState(Enum):
    COMMITTED = "committed"
    PENDING = "pending"
    CORRUPT = "corrupt"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactKey:
    artifact_id: ArtifactId
    kind: ArtifactKind

    def __str__(self) -> str:
        return f"{self.kind.value}:{self.artifact_id.value}"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactManifest:
    artifact_key: ArtifactKey
    format: ArtifactFormat
    state: ArtifactState
    relative_path: str
    scientific_fingerprint: Fingerprint
    execution_fingerprint: Fingerprint
    payload_checksum: Checksum
    schema_version: int = 1
    seed: Seed | None = None
