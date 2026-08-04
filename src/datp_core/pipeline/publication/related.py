"""Coordinated publication for one logical artifact spanning related directories."""

from dataclasses import dataclass
from pathlib import Path
from shutil import rmtree
from typing import Protocol

from filelock import FileLock

from datp_core.domain.enums import PublicationStatus
from datp_core.pipeline.publication.atomic import cleanup_staging_directory, create_staging_directory


@dataclass(frozen=True, slots=True, kw_only=True)
class RelatedPublicationMember:
    identity: str
    target: Path

    def __post_init__(self) -> None:
        if not self.identity:
            raise ValueError("related publication member identity must be non-empty")


class RelatedArtifactCodec[RequestT, ResultT](Protocol):
    def write(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT: ...

    def validate(self, request: RequestT, directories: tuple[Path, ...]) -> bool: ...

    def load(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT: ...

    def rebase(self, result: ResultT, directories: tuple[Path, ...]) -> ResultT: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class RelatedArtifactPublication[RequestT, ResultT]:
    request: RequestT
    members: tuple[RelatedPublicationMember, ...]
    codec: RelatedArtifactCodec[RequestT, ResultT]
    overwrite: bool

    def __post_init__(self) -> None:
        if len(self.members) < 2:
            raise ValueError("related artifact publication requires at least two members")
        identities = tuple(member.identity for member in self.members)
        targets = tuple(member.target for member in self.members)
        if len(frozenset(identities)) != len(identities):
            raise ValueError("related publication member identities must be unique")
        if len(frozenset(targets)) != len(targets):
            raise ValueError("related publication targets must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class RelatedArtifactPublicationResult[ResultT]:
    status: PublicationStatus
    value: ResultT


def publish_related_artifacts[RequestT, ResultT](
    publication: RelatedArtifactPublication[RequestT, ResultT],
) -> RelatedArtifactPublicationResult[ResultT]:
    """Publish related directories under one lock with backup-based rollback."""
    targets = tuple(member.target for member in publication.members)
    lock_path = targets[0].with_name(f".{targets[0].name}.related.lock")
    with FileLock(str(lock_path)):
        if not publication.overwrite and publication.codec.validate(publication.request, targets):
            loaded = publication.codec.load(publication.request, targets)
            return RelatedArtifactPublicationResult(
                status=PublicationStatus.REUSED,
                value=publication.codec.rebase(loaded, targets),
            )
        staging = tuple(create_staging_directory(target) for target in targets)
        backups = tuple(target.with_name(f".{target.name}.backup") for target in targets)
        try:
            result = publication.codec.write(publication.request, staging)
            _remove_paths(backups)
            for target, backup in zip(targets, backups, strict=True):
                if target.exists():
                    target.replace(backup)
            try:
                for staged, target in zip(staging, targets, strict=True):
                    staged.replace(target)
            except Exception:
                _remove_paths(targets)
                for backup, target in zip(backups, targets, strict=True):
                    if backup.exists():
                        backup.replace(target)
                raise
            _remove_paths(backups)
        except Exception:
            for staged in staging:
                cleanup_staging_directory(staged, ignore_errors=True)
            raise
    return RelatedArtifactPublicationResult(
        status=PublicationStatus.PUBLISHED,
        value=publication.codec.rebase(result, targets),
    )


def _remove_paths(paths: tuple[Path, ...]) -> None:
    for path in paths:
        if path.is_dir():
            rmtree(path)
        elif path.exists():
            path.unlink()
