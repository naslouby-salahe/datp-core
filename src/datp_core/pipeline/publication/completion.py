"""Completion-marker construction and strict validation."""

from __future__ import annotations

from datp_core.pipeline.publication.records import ArtifactRecord, ArtifactState, CompletionRecord


def build_completion_record(
    *,
    plan_digest: str,
    campaign_digest: str,
    artifacts: tuple[ArtifactRecord, ...],
) -> CompletionRecord:
    return CompletionRecord(
        plan_digest=plan_digest,
        campaign_digest=campaign_digest,
        artifacts=artifacts,
        complete=bool(artifacts) and all(item.state is ArtifactState.PUBLISHED for item in artifacts),
    )


def require_complete(record: CompletionRecord) -> None:
    if not record.complete:
        raise ValueError("experiment publication is incomplete")
    invalid = tuple(item for item in record.artifacts if item.state is not ArtifactState.PUBLISHED)
    if invalid:
        raise ValueError("experiment publication contains non-published artifacts")
