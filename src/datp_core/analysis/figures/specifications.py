from datp_core.analysis.report_models import (
    FigureSeries,
    HeatmapCell,
    HeatmapFigureSpecification,
    SeriesFigureSpecification,
)
from datp_core.domain.experiments.protocols import FigureType


def cdf_overlay_figure(
    horizontal_label: str, vertical_label: str, series: tuple[FigureSeries, ...]
) -> SeriesFigureSpecification:
    return _series_figure(FigureType.CDF_OVERLAY, horizontal_label, vertical_label, series)


def scatter_figure(
    horizontal_label: str, vertical_label: str, series: tuple[FigureSeries, ...]
) -> SeriesFigureSpecification:
    return _series_figure(FigureType.SCATTER, horizontal_label, vertical_label, series)


def heatmap_figure(
    horizontal_label: str, vertical_label: str, intensity_label: str, cells: tuple[HeatmapCell, ...]
) -> HeatmapFigureSpecification:
    return HeatmapFigureSpecification(
        figure_type=FigureType.HEATMAP,
        horizontal_label=horizontal_label,
        vertical_label=vertical_label,
        intensity_label=intensity_label,
        cells=cells,
    )


def lambda_curve_figure(
    horizontal_label: str, vertical_label: str, series: tuple[FigureSeries, ...]
) -> SeriesFigureSpecification:
    return _series_figure(FigureType.LAMBDA_CURVE, horizontal_label, vertical_label, series)


def recovery_curve_figure(
    horizontal_label: str, vertical_label: str, series: tuple[FigureSeries, ...]
) -> SeriesFigureSpecification:
    return _series_figure(FigureType.RECOVERY_CURVE, horizontal_label, vertical_label, series)


def severity_trend_figure(
    horizontal_label: str, vertical_label: str, series: tuple[FigureSeries, ...]
) -> SeriesFigureSpecification:
    return _series_figure(FigureType.SEVERITY_TREND, horizontal_label, vertical_label, series)


def _series_figure(
    figure_type: FigureType,
    horizontal_label: str,
    vertical_label: str,
    series: tuple[FigureSeries, ...],
) -> SeriesFigureSpecification:
    return SeriesFigureSpecification(
        figure_type=figure_type,
        horizontal_label=horizontal_label,
        vertical_label=vertical_label,
        series=series,
    )
