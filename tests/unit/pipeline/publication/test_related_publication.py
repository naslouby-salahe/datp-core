from dataclasses import dataclass
from pathlib import Path

import pytest

from datp_core.artifacts.repositories.publication import (
    RelatedArtifactPublication,
    RelatedPublicationMember,
    publish_related_artifacts,
)
from datp_core.core.identifiers import PublicationStatus, RelatedPublicationMemberIdentity


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
        RelatedPublicationMember(identity=RelatedPublicationMemberIdentity("global"), target=tmp_path / "global"),
        RelatedPublicationMember(
            identity=RelatedPublicationMemberIdentity("personalized"),
            target=tmp_path / "personalized",
        ),
    )
    request = _Request("global", "personalized")
    publication = RelatedArtifactPublication(request=request, members=members, codec=_Codec(), overwrite=False)
    first = publish_related_artifacts(publication)
    second = publish_related_artifacts(publication)
    assert first.status is PublicationStatus.PUBLISHED
    assert second.status is PublicationStatus.REUSED
    assert first.value == second.value


def test_related_publication_interrupted_write_leaves_no_staging_or_target(tmp_path: Path) -> None:
    class _FailingCodec:
        def write(self, request: _Request, directories: tuple[Path, ...]) -> _Result:
            del request, directories
            raise RuntimeError("interrupted write")

        def validate(self, request: _Request, directories: tuple[Path, ...]) -> bool:
            del request, directories
            return False

        def load(self, request: _Request, directories: tuple[Path, ...]) -> _Result:
            raise AssertionError("load must not run when the artifact is not reusable")

        def rebase(self, result: _Result, directories: tuple[Path, ...]) -> _Result:
            raise AssertionError("rebase must not run when the write failed")

    members = (
        RelatedPublicationMember(identity=RelatedPublicationMemberIdentity("global"), target=tmp_path / "global"),
        RelatedPublicationMember(
            identity=RelatedPublicationMemberIdentity("personalized"),
            target=tmp_path / "personalized",
        ),
    )
    publication = RelatedArtifactPublication(
        request=_Request("global", "personalized"),
        members=members,
        codec=_FailingCodec(),
        overwrite=False,
    )
    with pytest.raises(RuntimeError, match="interrupted write"):
        publish_related_artifacts(publication)
    assert not (tmp_path / "global").exists()
    assert not (tmp_path / "personalized").exists()
    assert tuple(path for path in tmp_path.iterdir() if path.is_dir()) == ()


def test_related_publication_rolls_back_every_target_when_a_later_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    members = (
        RelatedPublicationMember(identity=RelatedPublicationMemberIdentity("global"), target=tmp_path / "global"),
        RelatedPublicationMember(
            identity=RelatedPublicationMemberIdentity("personalized"),
            target=tmp_path / "personalized",
        ),
    )
    original_request = _Request("original-global", "original-personalized")
    publish_related_artifacts(
        RelatedArtifactPublication(request=original_request, members=members, codec=_Codec(), overwrite=False)
    )

    real_replace = Path.replace
    personalized_target = tmp_path / "personalized"
    personalized_staging_prefix = f".{personalized_target.name}."
    failure_injected = False

    def _flaky_replace(self: Path, target: Path) -> Path:
        nonlocal failure_injected
        if not failure_injected and target == personalized_target and self.name.startswith(personalized_staging_prefix):
            failure_injected = True
            raise OSError("simulated failure replacing the second related target")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", _flaky_replace)
    overwrite_request = _Request("new-global", "new-personalized")
    publication = RelatedArtifactPublication(
        request=overwrite_request,
        members=members,
        codec=_Codec(),
        overwrite=True,
    )
    with pytest.raises(OSError, match="simulated failure"):
        publish_related_artifacts(publication)
    monkeypatch.undo()

    assert (tmp_path / "global" / "global.txt").read_text(encoding="utf-8") == "original-global"
    assert (tmp_path / "personalized" / "personalized.txt").read_text(encoding="utf-8") == "original-personalized"
