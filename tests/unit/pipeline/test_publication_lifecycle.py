from pathlib import Path

from datp_core.pipeline.publication.completion import build_completion_record, require_complete
from datp_core.pipeline.publication.records import ArtifactKind, ArtifactRecord, ArtifactState
from datp_core.pipeline.publication.reload_validation import validate_reload


def test_completion_and_reload_require_exact_published_artifacts(tmp_path: Path) -> None:
    relative = Path("result.json")
    payload = b"{}"
    (tmp_path / relative).write_bytes(payload)
    artifact = ArtifactRecord(
        kind=ArtifactKind.SUMMARY,
        relative_path=relative,
        checksum="digest",
        byte_count=len(payload),
        state=ArtifactState.PUBLISHED,
    )
    completion = build_completion_record(
        plan_digest="plan",
        campaign_digest="campaign",
        artifacts=(artifact,),
    )
    require_complete(completion)
    validation = validate_reload(root=tmp_path, completion=completion, observed=(artifact,))
    assert validation.valid
