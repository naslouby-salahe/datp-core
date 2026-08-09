"""Shared artifact, completion, and experiment-manifest contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import ConfigDict, model_validator

from datp_core.artifacts.provenance import Checksum
from datp_core.core.contracts import StrictModel
from datp_core.core.numeric import ByteCount


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


class CompletionRecord(StrictModel):
    model_config = ConfigDict(revalidate_instances="never")
    plan_digest: Checksum
    campaign_digest: Checksum
    protocol_digest: Checksum
    artifacts: tuple[ArtifactRecord, ...]
    state: CompletionState

    @model_validator(mode="after")
    def _validate_artifacts(self) -> CompletionRecord:
        paths = tuple(item.relative_path for item in self.artifacts)
        if len(paths) != len(frozenset(paths)):
            raise ValueError("completion-record artifact paths must be unique")
        if self.state is CompletionState.COMPLETE and not self.artifacts:
            raise ValueError("complete records require at least one published artifact")
        if self.state is CompletionState.COMPLETE and any(
            item.state is not ArtifactState.PUBLISHED for item in self.artifacts
        ):
            raise ValueError("complete records may contain only published artifacts")
        return self

    @property
    def complete(self) -> bool:
        return self.state is CompletionState.COMPLETE
