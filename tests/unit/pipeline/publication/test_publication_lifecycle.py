from pathlib import Path

import pytest

from datp_core.domain.values import ByteCount, Checksum, checksum_bytes
from datp_core.pipeline.publication.models import (
    ArtifactKind,
    ArtifactRecord,
    ArtifactState,
    CompletionRecord,
    CompletionState,
)
from datp_core.pipeline.publication.service import (
    build_completion_record,
    read_completion_record,
    require_complete,
    validate_reload,
    write_completion_record,
)


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


def test_completion_record_round_trips_through_disk(tmp_path: Path) -> None:
    relative = Path("result.json")
    payload = b"{}"
    artifact = artifact_for(relative, payload)
    record = build_completion_record(
        plan_digest="plan",
        campaign_digest="campaign",
        artifacts=(artifact,),
    )

    write_completion_record(tmp_path, record)
    reloaded = read_completion_record(tmp_path)

    assert reloaded == record


def test_read_completion_record_returns_none_when_absent_or_corrupt(tmp_path: Path) -> None:
    assert read_completion_record(tmp_path) is None
    (tmp_path / "completion.json").write_text("not json", encoding="utf-8")
    assert read_completion_record(tmp_path) is None
