from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import PublicationStatus
from datp_core.pipeline.publication.codec import (
    ArtifactPublication,
    publish_artifact,
)


@dataclass(frozen=True, slots=True)
class _Request:
    payload: str


@dataclass(frozen=True, slots=True)
class _Result:
    path: Path
    payload: str


class _Codec:
    def write(self, request: _Request, directory: Path) -> _Result:
        path = directory / "payload.txt"
        path.write_text(request.payload, encoding="utf-8")
        (directory / "COMPLETE").write_text(request.payload, encoding="utf-8")
        return _Result(path=path, payload=request.payload)

    def validate(self, request: _Request, directory: Path) -> bool:
        payload = directory / "payload.txt"
        complete = directory / "COMPLETE"
        return (
            payload.is_file()
            and complete.is_file()
            and payload.read_text(encoding="utf-8") == request.payload
            and complete.read_text(encoding="utf-8") == request.payload
        )

    def load(self, request: _Request, directory: Path) -> _Result:
        path = directory / "payload.txt"
        return _Result(path=path, payload=path.read_text(encoding="utf-8"))

    def rebase(self, result: _Result, directory: Path) -> _Result:
        return _Result(path=directory / result.path.name, payload=result.payload)


def test_artifact_codec_publishes_reuses_and_rebases(tmp_path: Path) -> None:
    target = tmp_path / "artifact"
    publication = ArtifactPublication(
        target=target,
        request=_Request(payload="stable"),
        codec=_Codec(),
        overwrite=False,
    )
    first = publish_artifact(publication)
    second = publish_artifact(publication)
    assert first.status is PublicationStatus.PUBLISHED
    assert second.status is PublicationStatus.REUSED
    assert first.value.path == target / "payload.txt"
    assert second.value == first.value
