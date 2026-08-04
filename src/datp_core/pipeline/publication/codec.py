"""Typed artifact codecs for one shared write, validate, load, and rebase lifecycle."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from datp_core.domain.enums import PublicationStatus
from datp_core.pipeline.publication.atomic import publish_atomically


class ArtifactCodec[RequestT, ResultT](Protocol):
    def write(self, request: RequestT, directory: Path) -> ResultT: ...

    def validate(self, request: RequestT, directory: Path) -> bool: ...

    def load(self, request: RequestT, directory: Path) -> ResultT: ...

    def rebase(self, result: ResultT, directory: Path) -> ResultT: ...


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
