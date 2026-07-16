from datp_core.analysis.report_models import TableSpecification
from datp_core.analysis.wording import ClaimWording
from datp_core.application.ports.reporting import RenderedReportArtifact, RenderReportArtifactRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.infrastructure.reporting.validation import (
    rendering_error,
    validate_table_request,
    validate_wording_request,
)


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
        raise rendering_error(request, "LaTex renderer received an unsupported serialization format")
    specification = request.traced_specification.specification
    if isinstance(specification, TableSpecification):
        validate_table_request(request)
        return specification
    if isinstance(specification, ClaimWording):
        validate_wording_request(request)
        return specification
    raise rendering_error(request, "LaTex renderer accepts tables and wording blocks only")


def _latex_table(specification: TableSpecification) -> str:
    alignment = "l" * len(specification.columns)
    header = " & ".join(column.label for column in specification.columns) + r" \\"
    rows = tuple(" & ".join(str(value) for value in row.values) + r" \\" for row in specification.rows)
    return "\n".join((rf"\begin{{tabular}}{{{alignment}}}", header, *rows, r"\end{tabular}"))
