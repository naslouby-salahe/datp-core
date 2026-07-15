from decimal import Decimal
from inspect import signature

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datp_core.analysis.figures.specifications import cdf_overlay_figure
from datp_core.analysis.report_models import CartesianPoint, FigureSeries, ReportColumn, ReportRow, TableSpecification
from datp_core.application.ports.reporting import RenderReportArtifactRequest
from datp_core.application.reporting.freeze import ResultFreezeEligibility
from datp_core.application.reporting.tracing import TableFigureTracer, TraceReportArtifactRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import (
    ArtifactId,
    ArtifactRef,
    ArtifactReferenceCollection,
    ArtifactSchemaVersion,
)
from datp_core.domain.errors import ProvenanceError, ReportingError
from datp_core.domain.experiments.feasibility import ScientificReadinessResult
from datp_core.domain.experiments.protocols import FigureType, ReportArtifactType, TableType
from datp_core.infrastructure.reporting.latex import LatexReportRenderer
from datp_core.infrastructure.reporting.markdown import MarkdownReportRenderer
from datp_core.infrastructure.reporting.matplotlib import MatplotlibReportRenderer


def _artifact(character: str, artifact_type: ArtifactType, format: SerializationFormat) -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value=f"artifact-{character * 64}"),
        artifact_type=artifact_type,
        content_hash=character * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=format,
    )


def _table() -> TableSpecification:
    return TableSpecification(
        table_type=TableType.CONFIRMATORY_INTERVAL,
        columns=(ReportColumn(key="estimate", label="Estimate"), ReportColumn(key="note", label="Note")),
        rows=(ReportRow(values=(Decimal("0.123456789012"), "quoted, value")),),
    )


def _traced_table() -> RenderReportArtifactRequest:
    source = _artifact("a", ArtifactType.TABLE_INPUT, SerializationFormat.JSON)
    traced = TableFigureTracer().trace(
        TraceReportArtifactRequest(
            output=_artifact("b", ArtifactType.RENDERED_TABLE, SerializationFormat.MARKDOWN),
            specification=_table(),
            required_inputs=ArtifactReferenceCollection(references=(source,)),
            provenance_chain=ArtifactReferenceCollection(references=(source,)),
            result_freeze=ResultFreezeEligibility(
                result_freeze=_artifact("c", ArtifactType.RESULT_FREEZE, SerializationFormat.JSON),
                readiness=ScientificReadinessResult(blockers=()),
            ),
        )
    )
    return RenderReportArtifactRequest(
        traced_specification=traced,
        artifact_type=ReportArtifactType.MAIN_TABLE,
        format=SerializationFormat.MARKDOWN,
    )


def _traced_figure(format: SerializationFormat) -> RenderReportArtifactRequest:
    source = _artifact("d", ArtifactType.FIGURE_INPUT, SerializationFormat.JSON)
    specification = cdf_overlay_figure(
        "score",
        "cdf",
        (FigureSeries(label="observed", points=(CartesianPoint(horizontal=1, vertical=0.123456789012),)),),
    )
    assert specification.figure_type is FigureType.CDF_OVERLAY
    traced = TableFigureTracer().trace(
        TraceReportArtifactRequest(
            output=_artifact("e", ArtifactType.RENDERED_FIGURE, format),
            specification=specification,
            required_inputs=ArtifactReferenceCollection(references=(source,)),
            provenance_chain=ArtifactReferenceCollection(references=(source,)),
            result_freeze=ResultFreezeEligibility(
                result_freeze=_artifact("f", ArtifactType.RESULT_FREEZE, SerializationFormat.JSON),
                readiness=ScientificReadinessResult(blockers=()),
            ),
        )
    )
    return RenderReportArtifactRequest(
        traced_specification=traced,
        artifact_type=ReportArtifactType.FIGURE,
        format=format,
    )


@pytest.mark.parametrize(
    "format",
    (SerializationFormat.MARKDOWN, SerializationFormat.CSV, SerializationFormat.PARQUET, SerializationFormat.JSON),
)
def test_markdown_renderer_preserves_every_table_value_without_rounding(format: SerializationFormat) -> None:
    request = _traced_table()
    request = RenderReportArtifactRequest(
        traced_specification=request.traced_specification,
        artifact_type=request.artifact_type,
        format=format,
    )

    rendered = MarkdownReportRenderer().render(request)

    if format is SerializationFormat.PARQUET:
        assert rendered.content.startswith(b"PAR1")
        assert rendered.content.endswith(b"PAR1")
        assert pq.read_table(pa.BufferReader(rendered.content)).column(0).to_pylist() == [Decimal("0.123456789012")]
    else:
        content = rendered.content.decode()
        assert "0.123456789012" in content
        assert "quoted, value" in content
    assert rendered.artifact is request.traced_specification.output


@pytest.mark.parametrize("renderer", (MarkdownReportRenderer(), LatexReportRenderer(), MatplotlibReportRenderer()))
def test_every_renderer_implements_the_exact_report_renderer_port_signature(
    renderer: MarkdownReportRenderer | LatexReportRenderer | MatplotlibReportRenderer,
) -> None:
    parameters = tuple(signature(renderer.render).parameters)

    assert parameters == ("request",)


def test_latex_renderer_preserves_every_table_value_without_rounding() -> None:
    request = _traced_table()
    rendered = LatexReportRenderer().render(
        RenderReportArtifactRequest(
            traced_specification=request.traced_specification,
            artifact_type=request.artifact_type,
            format=SerializationFormat.LATEX,
        )
    )

    assert b"0.123456789012" in rendered.content
    assert b"quoted, value" in rendered.content


@pytest.mark.parametrize(
    ("format", "signature"),
    ((SerializationFormat.SVG, b"<?xml"), (SerializationFormat.PNG, b"\x89PNG"), (SerializationFormat.PDF, b"%PDF")),
)
def test_matplotlib_renderer_renders_each_supported_figure_format_without_mutating_specification(
    format: SerializationFormat, signature: bytes
) -> None:
    request = _traced_figure(format)
    original = request.traced_specification.specification

    rendered = MatplotlibReportRenderer().render(request)

    assert rendered.content.startswith(signature)
    assert request.traced_specification.specification == original


def test_trace_refusal_prevents_any_renderer_request_from_existing() -> None:
    source = _artifact("a", ArtifactType.TABLE_INPUT, SerializationFormat.JSON)
    request = TraceReportArtifactRequest(
        output=_artifact("b", ArtifactType.RENDERED_TABLE, SerializationFormat.MARKDOWN),
        specification=_table(),
        required_inputs=ArtifactReferenceCollection(references=(source,)),
        provenance_chain=ArtifactReferenceCollection(references=()),
        result_freeze=ResultFreezeEligibility(
            result_freeze=_artifact("c", ArtifactType.RESULT_FREEZE, SerializationFormat.JSON),
            readiness=ScientificReadinessResult(blockers=()),
        ),
    )
    tracer = TableFigureTracer()

    with pytest.raises(ProvenanceError):
        tracer.trace(request)


@pytest.mark.parametrize("renderer", (MarkdownReportRenderer(), LatexReportRenderer(), MatplotlibReportRenderer()))
def test_renderer_rejects_a_traced_specification_for_an_incompatible_format(
    renderer: MarkdownReportRenderer | LatexReportRenderer | MatplotlibReportRenderer,
) -> None:
    request = (
        _traced_table() if isinstance(renderer, MatplotlibReportRenderer) else _traced_figure(SerializationFormat.PNG)
    )
    request = RenderReportArtifactRequest(
        traced_specification=request.traced_specification,
        artifact_type=request.artifact_type,
        format=SerializationFormat.PNG,
    )
    with pytest.raises(ReportingError):
        renderer.render(request)
