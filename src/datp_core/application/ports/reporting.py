from dataclasses import dataclass
from typing import Protocol

from datp_core.application.reporting.contracts import TracedReportSpecification
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.references import ArtifactRef
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.protocols import ReportArtifactType


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderReportArtifactRequest:
    traced_specification: TracedReportSpecification
    artifact_type: ReportArtifactType
    format: SerializationFormat

    def __post_init__(self) -> None:
        if not _has_render_request_components(self):
            raise DomainValidationError(
                detail="report rendering requires a trace-gated specification and typed output selection",
                value=repr(self),
                constraint="TracedReportSpecification, ReportArtifactType, SerializationFormat",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class RenderedReportArtifact:
    artifact: ArtifactRef
    content: bytes


def _has_render_request_components(request: RenderReportArtifactRequest) -> bool:
    return all(
        (
            type(request.traced_specification) is TracedReportSpecification,
            type(request.artifact_type) is ReportArtifactType,
            type(request.format) is SerializationFormat,
        )
    )


class ReportRenderer(Protocol):
    def render(self, request: RenderReportArtifactRequest) -> RenderedReportArtifact: ...
