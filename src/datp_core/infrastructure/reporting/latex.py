from datp_core.analysis.report_models import TableSpecification
from datp_core.analysis.wording import ClaimWording
from datp_core.application.ports.reporting import RenderedReportArtifact, RenderReportArtifactRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.errors import ReportingError
from datp_core.domain.experiments.protocols import ReportArtifactType


class LatexReportRenderer:
    def render(self, request: RenderReportArtifactRequest) -> RenderedReportArtifact:
        specification = _validated_latex_specification(request)
        if isinstance(specification, TableSpecification):
            content = _latex_table(specification)
        else:
            content = specification.template
        return RenderedReportArtifact(artifact=request.traced_specification.output, content=content.encode())


def _validated_latex_specification(request: RenderReportArtifactRequest) -> TableSpecification | ClaimWording:
    if request.format is not SerializationFormat.LATEX:
        raise _rendering_error(request, "LaTex renderer received an unsupported serialization format")
    specification = request.traced_specification.specification
    if isinstance(specification, TableSpecification):
        _validate_table_request(request)
        return specification
    if isinstance(specification, ClaimWording):
        _validate_wording_request(request)
        return specification
    raise _rendering_error(request, "LaTex renderer accepts tables and wording blocks only")


def _validate_table_request(request: RenderReportArtifactRequest) -> None:
    if request.traced_specification.output.artifact_type is not ArtifactType.RENDERED_TABLE:
        raise _rendering_error(request, "traced output artifact type does not match the table specification")
    if request.artifact_type not in {ReportArtifactType.MAIN_TABLE, ReportArtifactType.SUPPLEMENT_TABLE}:
        raise _rendering_error(request, "table specification received a non-table report artifact type")


def _validate_wording_request(request: RenderReportArtifactRequest) -> None:
    if request.traced_specification.output.artifact_type is not ArtifactType.WORDING_OUTPUT:
        raise _rendering_error(request, "traced output artifact type does not match the wording specification")
    if request.artifact_type is not ReportArtifactType.WORDING_BLOCK:
        raise _rendering_error(request, "wording specification received a non-wording report artifact type")


def _latex_table(specification: TableSpecification) -> str:
    alignment = "l" * len(specification.columns)
    header = " & ".join(column.label for column in specification.columns) + r" \\"
    rows = tuple(" & ".join(str(value) for value in row.values) + r" \\" for row in specification.rows)
    return "\n".join((rf"\begin{{tabular}}{{{alignment}}}", header, *rows, r"\end{tabular}"))


def _rendering_error(request: RenderReportArtifactRequest, cause: str) -> ReportingError:
    return ReportingError(
        detail="report rendering failed", output_id=request.traced_specification.output.artifact_id.value, cause=cause
    )
