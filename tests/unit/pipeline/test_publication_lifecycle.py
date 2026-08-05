from pathlib import Path

import pytest

from datp_core.domain.values import ByteCount, Checksum, checksum_bytes
from datp_core.pipeline.publication.completion import build_completion_record, require_complete
from datp_core.pipeline.publication.records import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactState,
    CompletionRecord,
    CompletionState,
)
from datp_core.pipeline.publication.reload_validation import validate_reload


def artifact_for(relative: Path, payload: bytes) -> ArtifactRecord:
    return ArtifactRecord(
        kind=ArtifactKind.SUMMARY,
        relative_path=relative,
        checksum=checksum_bytes(payload),
        byte_count=ByteCount(len(payload)),
        state=ArtifactState.PUBLISHED,
    )


def test_completion_and_reload_require_exact_published_artifacts(tmp_path: Path) -> None:
    relative = Path("result.json")
    payload = b"{}"
    (tmp_path / relative).write_bytes(payload)
    artifact = artifact_for(relative, payload)
    completion = build_completion_record(
        plan_digest="plan",
        campaign_digest="campaign",
        artifacts=(artifact,),
    )
    assert completion.state is CompletionState.COMPLETE
    require_complete(completion)
    validation = validate_reload(root=tmp_path, completion=completion, observed=(artifact,))
    assert validation.valid


def test_reload_detects_file_corruption_even_when_metadata_is_unchanged(tmp_path: Path) -> None:
    relative = Path("result.json")
    original = b"{}"
    artifact = artifact_for(relative, original)
    completion = build_completion_record(
        plan_digest="plan",
        campaign_digest="campaign",
        artifacts=(artifact,),
    )
    (tmp_path / relative).write_bytes(b'{"corrupt":true}')
    validation = validate_reload(root=tmp_path, completion=completion, observed=(artifact,))
    assert not validation.valid
    assert any("checksum mismatch" in item for item in validation.evidence)
    assert any("byte-count mismatch" in item for item in validation.evidence)


def test_reload_detects_missing_completed_artifact(tmp_path: Path) -> None:
    relative = Path("result.json")
    payload = b"{}"
    artifact = artifact_for(relative, payload)
    completion = build_completion_record(
        plan_digest="plan",
        campaign_digest="campaign",
        artifacts=(artifact,),
    )
    validation = validate_reload(root=tmp_path, completion=completion, observed=(artifact,))
    assert not validation.valid
    assert any("absent" in item for item in validation.evidence)


def test_artifact_paths_cannot_escape_publication_root() -> None:
    with pytest.raises(ValueError, match="publication root"):
        artifact_for(Path("..") / "result.json", b"{}")


def test_complete_record_requires_an_artifact_inventory() -> None:
    with pytest.raises(ValueError, match="at least one"):
        CompletionRecord(
            plan_digest=Checksum("plan"),
            campaign_digest=Checksum("campaign"),
            artifacts=(),
            state=CompletionState.COMPLETE,
        )
