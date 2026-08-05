"""Strict checksum, membership, state, and file validation for experiment publications."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
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
    evidence: list[str] = []
    expected_paths = tuple(item.relative_path for item in completion.artifacts)
    observed_paths = tuple(item.relative_path for item in observed)
    if not completion.complete:
        evidence.append("completion marker is not complete")
    if expected_paths != observed_paths:
        evidence.append("observed artifact ordering or membership differs from the completion record")
    expected_by_path = tuple((item.relative_path, item.checksum, item.byte_count) for item in completion.artifacts)
    observed_by_path = tuple((item.relative_path, item.checksum, item.byte_count) for item in observed)
    if expected_by_path != observed_by_path:
        evidence.append("artifact checksum or byte-count metadata mismatch")
    if any(item.state is not ArtifactState.PUBLISHED for item in observed):
        evidence.append("observed publication contains a non-published artifact")

    for artifact in completion.artifacts:
        artifact_path = root / artifact.relative_path
        if not artifact_path.is_file():
            evidence.append(f"completed artifact is absent: {artifact.relative_path.as_posix()}")
            continue
        payload = artifact_path.read_bytes()
        actual_checksum = blake2b(payload, digest_size=32).hexdigest()
        if actual_checksum != artifact.checksum:
            evidence.append(f"artifact checksum mismatch: {artifact.relative_path.as_posix()}")
        if len(payload) != artifact.byte_count:
            evidence.append(f"artifact byte-count mismatch: {artifact.relative_path.as_posix()}")

    return ReloadValidation(valid=not evidence, evidence=tuple(evidence))
