from datp_core.application.ports.reporting import RenderReportArtifactRequest
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.errors import ReportingError
from datp_core.domain.experiments.protocols import ReportArtifactType


def rendering_error(request: RenderReportArtifactRequest, cause: str) -> ReportingError:
    return ReportingError(
        detail="report rendering failed", output_id=request.traced_specification.output.artifact_id.value, cause=cause
    )


def validate_table_request(request: RenderReportArtifactRequest) -> None:
    if request.traced_specification.output.artifact_type is not ArtifactType.RENDERED_TABLE:
        raise rendering_error(request, "traced output artifact type does not match the table specification")
    if request.artifact_type not in {ReportArtifactType.MAIN_TABLE, ReportArtifactType.SUPPLEMENT_TABLE}:
        raise rendering_error(request, "table specification received a non-table report artifact type")


def validate_wording_request(request: RenderReportArtifactRequest) -> None:
    if request.traced_specification.output.artifact_type is not ArtifactType.WORDING_OUTPUT:
        raise rendering_error(request, "traced output artifact type does not match the wording specification")
    if request.artifact_type is not ReportArtifactType.WORDING_BLOCK:
        raise rendering_error(request, "wording specification received a non-wording report artifact type")
