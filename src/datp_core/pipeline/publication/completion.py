"""Completion-marker construction and strict validation."""

from __future__ import annotations

import json
from pathlib import Path

from datp_core.domain.values import ByteCount, Checksum, checksum_text
from datp_core.pipeline.publication.records import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactState,
    CompletionRecord,
    CompletionState,
)

COMPLETION_RECORD_ASSET = "completion.json"


def complete_digest(manifest_payload: str, schema_payload: str) -> Checksum:
    """Bind a manifest and schema payload into one deterministic completion digest."""
    return checksum_text(f"{manifest_payload}\n{schema_payload}")


def build_completion_record(
    *,
    plan_digest: Checksum | str,
    campaign_digest: Checksum | str,
    artifacts: tuple[ArtifactRecord, ...],
) -> CompletionRecord:
    state = (
        CompletionState.COMPLETE
        if artifacts and all(item.state is ArtifactState.PUBLISHED for item in artifacts)
        else CompletionState.INCOMPLETE
    )
    return CompletionRecord(
        plan_digest=plan_digest if isinstance(plan_digest, Checksum) else Checksum(plan_digest),
        campaign_digest=campaign_digest if isinstance(campaign_digest, Checksum) else Checksum(campaign_digest),
        artifacts=artifacts,
        state=state,
    )


def require_complete(record: CompletionRecord) -> None:
    if record.state is not CompletionState.COMPLETE:
        raise ValueError("experiment publication is incomplete")
    invalid = tuple(item for item in record.artifacts if item.state is not ArtifactState.PUBLISHED)
    if invalid:
        raise ValueError("experiment publication contains non-published artifacts")


def write_completion_record(directory: Path, record: CompletionRecord) -> Path:
    """Persist one completion record as canonical JSON. Artifact paths are recorded
    exactly as given (typically relative to a shared output root, not this directory,
    so reusable assets are referenced rather than copied)."""
    payload = {
        "plan_digest": record.plan_digest.value,
        "campaign_digest": record.campaign_digest.value,
        "state": record.state.value,
        "artifacts": [
            {
                "kind": item.kind.value,
                "relative_path": item.relative_path.as_posix(),
                "checksum": item.checksum.value,
                "byte_count": item.byte_count.value,
                "state": item.state.value,
            }
            for item in record.artifacts
        ],
    }
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / COMPLETION_RECORD_ASSET
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")), encoding="utf-8")
    return path


def read_completion_record(directory: Path) -> CompletionRecord | None:
    """Reload one completion record, or None if absent, unreadable, or structurally invalid."""
    path = directory / COMPLETION_RECORD_ASSET
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CompletionRecord(
            plan_digest=Checksum(payload["plan_digest"]),
            campaign_digest=Checksum(payload["campaign_digest"]),
            state=CompletionState(payload["state"]),
            artifacts=tuple(
                ArtifactRecord(
                    kind=ArtifactKind(item["kind"]),
                    relative_path=Path(item["relative_path"]),
                    checksum=Checksum(item["checksum"]),
                    byte_count=ByteCount(item["byte_count"]),
                    state=ArtifactState(item["state"]),
                )
                for item in payload["artifacts"]
            ),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None
