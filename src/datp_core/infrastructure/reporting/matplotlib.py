from io import BytesIO

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Axes, Figure

from datp_core.analysis.report_models import HeatmapFigureSpecification, SeriesFigureSpecification
from datp_core.application.ports.reporting import RenderedReportArtifact, RenderReportArtifactRequest
from datp_core.domain.artifacts.keys import SerializationFormat
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.experiments.protocols import ReportArtifactType
from datp_core.infrastructure.reporting.validation import rendering_error


class MatplotlibReportRenderer:
    def render(self, request: RenderReportArtifactRequest) -> RenderedReportArtifact:
        _validate_matplotlib_request(request)
        figure = _build_figure(request)
        buffer = BytesIO()
        figure.savefig(buffer, format=request.format.value, metadata={"Date": None})
        return RenderedReportArtifact(artifact=request.traced_specification.output, content=buffer.getvalue())


def _validate_matplotlib_request(request: RenderReportArtifactRequest) -> None:
    if request.format not in (SerializationFormat.SVG, SerializationFormat.PNG, SerializationFormat.PDF):
        raise rendering_error(request, "Matplotlib renderer received an unsupported serialization format")
    if request.traced_specification.output.artifact_type is not ArtifactType.RENDERED_FIGURE:
        raise rendering_error(request, "traced output artifact type does not match the figure specification")
    if request.artifact_type is not ReportArtifactType.FIGURE:
        raise rendering_error(request, "figure specification received a non-figure report artifact type")


def _build_figure(request: RenderReportArtifactRequest) -> Figure:
    specification = request.traced_specification.specification
    figure = Figure()
    FigureCanvasAgg(figure)
    axes = figure.subplots()
    if isinstance(specification, SeriesFigureSpecification):
        _render_series_figure(axes, specification)
    elif isinstance(specification, HeatmapFigureSpecification):
        _render_heatmap_figure(axes, specification)
    else:
        raise rendering_error(request, "Matplotlib renderer accepts figure specifications only")
    return figure


def _render_series_figure(axes: Axes, specification: SeriesFigureSpecification) -> None:
    for series in specification.series:
        axes.plot(
            tuple(point.horizontal for point in series.points),
            tuple(point.vertical for point in series.points),
            label=series.label,
        )
    axes.legend()
    axes.set_xlabel(specification.horizontal_label)
    axes.set_ylabel(specification.vertical_label)


def _render_heatmap_figure(axes: Axes, specification: HeatmapFigureSpecification) -> None:
    axes.scatter(
        tuple(cell.horizontal for cell in specification.cells),
        tuple(cell.vertical for cell in specification.cells),
        c=tuple(cell.intensity for cell in specification.cells),
    )
    axes.set_xlabel(specification.horizontal_label)
    axes.set_ylabel(specification.vertical_label)
