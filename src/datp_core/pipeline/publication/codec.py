"""Typed artifact codecs for shared write, validate, load, and rebase lifecycles."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from datp_core.domain.enums import PublicationStatus
from datp_core.pipeline.publication.atomic import publish_atomically, publish_related_atomically


class ArtifactCodec[RequestT, ResultT](Protocol):
    def write(self, request: RequestT, directory: Path) -> ResultT: ...

    def validate(self, request: RequestT, directory: Path) -> bool: ...

    def load(self, request: RequestT, directory: Path) -> ResultT: ...

    def rebase(self, result: ResultT, directory: Path) -> ResultT: ...


class RelatedArtifactCodec[RequestT, ResultT](Protocol):
    def write(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT: ...

    def validate(self, request: RequestT, directories: tuple[Path, ...]) -> bool: ...

    def load(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT: ...

    def rebase(self, result: ResultT, directories: tuple[Path, ...]) -> ResultT: ...


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionalArtifactCodec[RequestT, ResultT]:
    """Callable-backed codec used by thin orchestration adapters."""

    writer: Callable[[RequestT, Path], ResultT]
    validator: Callable[[RequestT, Path], bool]
    loader: Callable[[RequestT, Path], ResultT]
    rebaser: Callable[[ResultT, Path], ResultT]

    def write(self, request: RequestT, directory: Path) -> ResultT:
        return self.writer(request, directory)

    def validate(self, request: RequestT, directory: Path) -> bool:
        return self.validator(request, directory)

    def load(self, request: RequestT, directory: Path) -> ResultT:
        return self.loader(request, directory)

    def rebase(self, result: ResultT, directory: Path) -> ResultT:
        return self.rebaser(result, directory)


@dataclass(frozen=True, slots=True, kw_only=True)
class FunctionalRelatedArtifactCodec[RequestT, ResultT]:
    """Callable-backed related-directory codec used by orchestration adapters."""

    writer: Callable[[RequestT, tuple[Path, ...]], ResultT]
    validator: Callable[[RequestT, tuple[Path, ...]], bool]
    loader: Callable[[RequestT, tuple[Path, ...]], ResultT]
    rebaser: Callable[[ResultT, tuple[Path, ...]], ResultT]

    def write(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT:
        return self.writer(request, directories)

    def validate(self, request: RequestT, directories: tuple[Path, ...]) -> bool:
        return self.validator(request, directories)

    def load(self, request: RequestT, directories: tuple[Path, ...]) -> ResultT:
        return self.loader(request, directories)

    def rebase(self, result: ResultT, directories: tuple[Path, ...]) -> ResultT:
        return self.rebaser(result, directories)


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactPublication[RequestT, ResultT]:
    target: Path
    request: RequestT
    codec: ArtifactCodec[RequestT, ResultT]
    overwrite: bool
    complete_marker: str | Path = "COMPLETE"


@dataclass(frozen=True, slots=True, kw_only=True)
class ArtifactPublicationResult[ResultT]:
    status: PublicationStatus
    value: ResultT


@dataclass(frozen=True, slots=True, kw_only=True)
class RelatedPublicationMember:
    identity: str
    target: Path

    def __post_init__(self) -> None:
        if not self.identity:
            raise ValueError("related publication member identity must be non-empty")


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


def publish_artifact[RequestT, ResultT](
    publication: ArtifactPublication[RequestT, ResultT],
) -> ArtifactPublicationResult[ResultT]:
    """Execute the common artifact lifecycle exactly once for every feature codec."""
    codec = publication.codec
    request = publication.request
    outcome = publish_atomically(
        target=publication.target,
        overwrite=publication.overwrite,
        is_reusable=lambda directory: codec.validate(request, directory),
        write=lambda directory: codec.write(request, directory),
        reusable_value=lambda directory: codec.load(request, directory),
        complete_marker=publication.complete_marker,
    )
    return ArtifactPublicationResult(
        status=outcome.status,
        value=codec.rebase(outcome.value, publication.target),
    )


def publish_related_artifacts[RequestT, ResultT](
    publication: RelatedArtifactPublication[RequestT, ResultT],
) -> RelatedArtifactPublicationResult[ResultT]:
    """Execute one transactional lifecycle for a related-directory artifact."""
    codec = publication.codec
    request = publication.request
    targets = tuple(member.target for member in publication.members)
    outcome = publish_related_atomically(
        targets=targets,
        overwrite=publication.overwrite,
        is_reusable=lambda directories: codec.validate(request, directories),
        write=lambda directories: codec.write(request, directories),
        reusable_value=lambda directories: codec.load(request, directories),
    )
    return RelatedArtifactPublicationResult(
        status=outcome.status,
        value=codec.rebase(outcome.value, targets),
    )
