"""Application-facing artifact repository port, independent of any filesystem implementation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from datp_core.artifacts.payloads import ArtifactCommitRequest
from datp_core.artifacts.repository.models import ArtifactCommitResult, ArtifactLookupResult


@runtime_checkable
class ArtifactRepository(Protocol):
    """Single application-facing authority for immutable artifact persistence."""

    def commit(self, request: ArtifactCommitRequest) -> ArtifactCommitResult: ...

    def read(self, relative_path: str) -> ArtifactLookupResult: ...

    def inspect(self, relative_path: str) -> ArtifactLookupResult: ...
