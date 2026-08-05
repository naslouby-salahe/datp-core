"""Completion-marker construction and strict validation."""

from __future__ import annotations

from datp_core.domain.values import Checksum, checksum_text
from datp_core.pipeline.publication.records import (
    ArtifactRecord,
    ArtifactState,
    CompletionRecord,
    CompletionState,
)


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
        plan_digest=plan_digest,
        campaign_digest=campaign_digest,
        artifacts=artifacts,
        state=state,
    )


def require_complete(record: CompletionRecord) -> None:
    if record.state is not CompletionState.COMPLETE:
        raise ValueError("experiment publication is incomplete")
    invalid = tuple(item for item in record.artifacts if item.state is not ArtifactState.PUBLISHED)
    if invalid:
        raise ValueError("experiment publication contains non-published artifacts")
