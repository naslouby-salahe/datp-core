from hashlib import blake2b
from pathlib import Path

from datp_core.pipeline.publication.completion import build_completion_record, require_complete
from datp_core.pipeline.publication.records import ArtifactKind, ArtifactRecord, ArtifactState
from datp_core.pipeline.publication.reload_validation import validate_reload


def artifact_for(relative: Path, payload: bytes) -> ArtifactRecord:
    return ArtifactRecord(
        kind=ArtifactKind.SUMMARY,
        relative_path=relative,
        checksum=blake2b(payload, digest_size=32).hexdigest(),
        byte_count=len(payload),
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
