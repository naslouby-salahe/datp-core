from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import PublicationStatus
from datp_core.pipeline.publication.related import (
    RelatedArtifactPublication,
    RelatedPublicationMember,
    publish_related_artifacts,
)


@dataclass(frozen=True, slots=True)
class _Request:
    global_payload: str
    personalized_payload: str


@dataclass(frozen=True, slots=True)
class _Result:
    global_path: Path
    personalized_path: Path


class _Codec:
    def write(self, request: _Request, directories: tuple[Path, ...]) -> _Result:
        global_path = directories[0] / "global.txt"
        personalized_path = directories[1] / "personalized.txt"
        global_path.write_text(request.global_payload, encoding="utf-8")
        personalized_path.write_text(request.personalized_payload, encoding="utf-8")
        return _Result(global_path, personalized_path)

    def validate(self, request: _Request, directories: tuple[Path, ...]) -> bool:
        global_path = directories[0] / "global.txt"
        personalized_path = directories[1] / "personalized.txt"
        return (
            global_path.is_file()
            and personalized_path.is_file()
            and global_path.read_text(encoding="utf-8") == request.global_payload
            and personalized_path.read_text(encoding="utf-8") == request.personalized_payload
        )

    def load(self, request: _Request, directories: tuple[Path, ...]) -> _Result:
        return _Result(directories[0] / "global.txt", directories[1] / "personalized.txt")

    def rebase(self, result: _Result, directories: tuple[Path, ...]) -> _Result:
        return _Result(directories[0] / result.global_path.name, directories[1] / result.personalized_path.name)


def test_related_publication_commits_and_reuses_all_members(tmp_path: Path) -> None:
    members = (
        RelatedPublicationMember(identity="global", target=tmp_path / "global"),
        RelatedPublicationMember(identity="personalized", target=tmp_path / "personalized"),
    )
    request = _Request("global", "personalized")
    publication = RelatedArtifactPublication(request=request, members=members, codec=_Codec(), overwrite=False)
    first = publish_related_artifacts(publication)
    second = publish_related_artifacts(publication)
    assert first.status is PublicationStatus.PUBLISHED
    assert second.status is PublicationStatus.REUSED
    assert first.value == second.value
