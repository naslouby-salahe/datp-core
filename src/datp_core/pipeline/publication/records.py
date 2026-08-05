"""Typed publication records for persisted experiment artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.domain.values import ByteCount, Checksum


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


class CompletionState(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactRecord:
    kind: ArtifactKind
    relative_path: Path
    checksum: Checksum
    byte_count: ByteCount
    state: ArtifactState

    def __post_init__(self) -> None:
        if self.relative_path.is_absolute() or not self.relative_path.parts:
            raise ValueError("artifact paths must be non-empty and relative")
        if ".." in self.relative_path.parts:
            raise ValueError("artifact paths must remain inside the publication root")
        if not isinstance(self.checksum, Checksum):
            object.__setattr__(self, "checksum", Checksum(self.checksum))
        if not isinstance(self.byte_count, ByteCount):
            object.__setattr__(self, "byte_count", ByteCount(self.byte_count))


@dataclass(frozen=True, slots=True, kw_only=True)
class CompletionRecord:
    plan_digest: Checksum
    campaign_digest: Checksum
    artifacts: tuple[ArtifactRecord, ...]
    state: CompletionState

    def __post_init__(self) -> None:
        if not isinstance(self.plan_digest, Checksum):
            object.__setattr__(self, "plan_digest", Checksum(self.plan_digest))
        if not isinstance(self.campaign_digest, Checksum):
            object.__setattr__(self, "campaign_digest", Checksum(self.campaign_digest))
        paths = tuple(item.relative_path for item in self.artifacts)
        if len(paths) != len(frozenset(paths)):
            raise ValueError("completion-record artifact paths must be unique")
        if self.state is CompletionState.COMPLETE and not self.artifacts:
            raise ValueError("complete records require at least one published artifact")
        if self.state is CompletionState.COMPLETE and any(
            item.state is not ArtifactState.PUBLISHED for item in self.artifacts
        ):
            raise ValueError("complete records may contain only published artifacts")

    @property
    def complete(self) -> bool:
        return self.state is CompletionState.COMPLETE
