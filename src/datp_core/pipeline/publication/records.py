"""Typed publication records for persisted experiment artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ArtifactKind(StrEnum):
    MANIFEST = "manifest"
    MODEL_TENSORS = "model_tensors"
    ESTIMATOR_STATE = "estimator_state"
    TABLE = "table"
    SUMMARY = "summary"
    FIGURE = "figure"
    COMPLETION = "completion"


class ArtifactState(StrEnum):
    PUBLISHED = "published"
    REUSED = "reused"
    INVALID = "invalid"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactRecord:
    kind: ArtifactKind
    relative_path: Path
    checksum: str
    byte_count: int
    state: ArtifactState

    def __post_init__(self) -> None:
        if self.relative_path.is_absolute() or not self.relative_path.parts:
            raise ValueError("artifact paths must be non-empty and relative")
        if not self.checksum.strip():
            raise ValueError("artifact checksums must be non-empty")
        if self.byte_count < 0:
            raise ValueError("artifact byte counts must be non-negative")


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletionRecord:
    plan_digest: str
    campaign_digest: str
    artifacts: tuple[ArtifactRecord, ...]
    complete: bool

    def __post_init__(self) -> None:
        if not self.plan_digest or not self.campaign_digest:
            raise ValueError("completion records require plan and campaign digests")
        paths = tuple(item.relative_path for item in self.artifacts)
        if len(paths) != len(frozenset(paths)):
            raise ValueError("completion-record artifact paths must be unique")
        if self.complete and any(item.state is not ArtifactState.PUBLISHED for item in self.artifacts):
            raise ValueError("complete records may contain only published artifacts")
