"""Safe reload validation for persisted experiment publications."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from datp_core.pipeline.publication.records import ArtifactRecord, ArtifactState, CompletionRecord


@dataclass(frozen=True, slots=True, kw_only=True)
class ReloadValidation:
    valid: bool
    evidence: tuple[str, ...]


def validate_reload(
    *,
    root: Path,
    completion: CompletionRecord,
    observed: tuple[ArtifactRecord, ...],
) -> ReloadValidation:
    expected_paths = tuple(item.relative_path for item in completion.artifacts)
    observed_paths = tuple(item.relative_path for item in observed)
    evidence: list[str] = []
    if not completion.complete:
        evidence.append("completion marker is not complete")
    if expected_paths != observed_paths:
        evidence.append("observed artifact ordering or membership differs from the completion record")
    expected_by_path = tuple((item.relative_path, item.checksum, item.byte_count) for item in completion.artifacts)
    observed_by_path = tuple((item.relative_path, item.checksum, item.byte_count) for item in observed)
    if expected_by_path != observed_by_path:
        evidence.append("artifact checksum or byte-count mismatch")
    missing = tuple(path for path in expected_paths if not (root / path).is_file())
    if missing:
        evidence.append("one or more completed artifacts are absent")
    if any(item.state is not ArtifactState.PUBLISHED for item in observed):
        evidence.append("observed publication contains a non-published artifact")
    return ReloadValidation(valid=not evidence, evidence=tuple(evidence))
