"""Publication figure specifications that cannot invent unavailable series."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.analysis.descriptive import ScoreGeometryResult, ScoreRole
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import (
    AnalysisReasonText,
    AvailabilityStatus,
    ClientIdentityToken,
    FederatedThresholdMethod,
    FigureLabel,
    FigureTitle,
    MetricId,
    ReportLine,
)
from datp_core.core.numeric import MetricValue, Seed, ThresholdValue


@dataclass(frozen=True, slots=True)
class ThresholdOverlay:
    method: FederatedThresholdMethod
    value: ThresholdValue


@dataclass(frozen=True, slots=True, kw_only=True)
class FigureSeries:
    label: FigureLabel
    metric: MetricId
    availability: AvailabilityStatus
    values: tuple[MetricValue, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.label, FigureLabel):
            object.__setattr__(self, "label", FigureLabel(self.label))
        if self.availability is not AvailabilityStatus.AVAILABLE and self.values:
            raise ValueError("unavailable figure series cannot contain values")
        if self.availability is AvailabilityStatus.AVAILABLE and not self.values:
            raise ValueError("available figure series require values")


@dataclass(frozen=True, slots=True, kw_only=True)
class EmpiricalCdfFigureSeries:
    """Typed empirical CDF series: x = reconstruction score, y = cumulative probability."""

    label: FigureLabel
    x_metric: MetricId
    y_metric: MetricId
    availability: AvailabilityStatus
    x_values: tuple[MetricValue, ...]
    y_values: tuple[MetricValue, ...]
    client_id: ClientIdentityToken | None
    seed: Seed | None
    score_role: ScoreRole | None
    threshold_overlays: tuple[ThresholdOverlay, ...]
    source_checksum: Checksum | None
    unavailable_reason: AnalysisReasonText | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.label, FigureLabel):
            object.__setattr__(self, "label", FigureLabel(self.label))
        if self.unavailable_reason is not None and not isinstance(self.unavailable_reason, AnalysisReasonText):
            object.__setattr__(self, "unavailable_reason", AnalysisReasonText(self.unavailable_reason))
        _validate_empirical_cdf_axes(self)
        if self.availability is AvailabilityStatus.AVAILABLE:
            _validate_available_empirical_cdf(self)
        else:
            _validate_unavailable_empirical_cdf(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class PairedMetricFigureSeries:
    """Reproducibility data for a labelled scatter or fitted paired-metric line."""

    label: FigureLabel
    x_label: FigureLabel
    y_label: FigureLabel
    availability: AvailabilityStatus
    x_values: tuple[MetricValue, ...]
    y_values: tuple[MetricValue, ...]
    point_labels: tuple[FigureLabel, ...] = ()
    unavailable_reason: AnalysisReasonText | None = None

    def __post_init__(self) -> None:
        _coerce_paired_metric_series_labels(self)
        if self.availability is AvailabilityStatus.AVAILABLE:
            _validate_available_paired_metric_series(self)
        else:
            _validate_unavailable_paired_metric_series(self)


def _coerce_paired_metric_series_labels(series: PairedMetricFigureSeries) -> None:
    for field_name, label_type in (
        ("label", FigureLabel),
        ("x_label", FigureLabel),
        ("y_label", FigureLabel),
        ("unavailable_reason", AnalysisReasonText),
    ):
        value = getattr(series, field_name)
        if value is not None and not isinstance(value, label_type):
            object.__setattr__(series, field_name, label_type(value))


def _validate_available_paired_metric_series(series: PairedMetricFigureSeries) -> None:
    if not series.x_values or len(series.x_values) != len(series.y_values):
        raise ValueError("available paired-metric series require aligned x and y values")
    if series.point_labels and len(series.point_labels) != len(series.x_values):
        raise ValueError("paired-metric point labels must cover every value pair")
    if series.unavailable_reason is not None:
        raise ValueError("available paired-metric series cannot carry an unavailable reason")


def _validate_unavailable_paired_metric_series(series: PairedMetricFigureSeries) -> None:
    if series.x_values or series.y_values or series.point_labels:
        raise ValueError("unavailable paired-metric series cannot contain values or point labels")
    if series.unavailable_reason is None:
        raise ValueError("unavailable paired-metric series require an explicit reason")


def _validate_empirical_cdf_axes(series: EmpiricalCdfFigureSeries) -> None:
    if series.x_metric is not MetricId.RECONSTRUCTION_ERROR and series.availability is AvailabilityStatus.AVAILABLE:
        raise ValueError("empirical reconstruction CDF series must use reconstruction-error x metric")
    if (
        series.y_metric is not MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY
        and series.availability is AvailabilityStatus.AVAILABLE
    ):
        raise ValueError("empirical CDF series must use cumulative-probability y metric")


def _validate_available_empirical_cdf(series: EmpiricalCdfFigureSeries) -> None:
    if not series.x_values or not series.y_values:
        raise ValueError("available empirical CDF series require x and y values")
    if len(series.x_values) != len(series.y_values):
        raise ValueError("empirical CDF x and y values must have equal length")
    if any(not (0.0 < y.value <= 1.0) for y in series.y_values):
        raise ValueError("empirical CDF y values must lie in (0, 1]")
    if any(left.value > right.value for left, right in zip(series.y_values, series.y_values[1:], strict=False)):
        raise ValueError("empirical CDF y values must be nondecreasing")
    if series.unavailable_reason is not None:
        raise ValueError("available empirical CDF series cannot carry an unavailable reason")


def _validate_unavailable_empirical_cdf(series: EmpiricalCdfFigureSeries) -> None:
    if series.x_values or series.y_values:
        raise ValueError("unavailable empirical CDF series cannot contain values")
    if series.unavailable_reason is None:
        raise ValueError("unavailable empirical CDF series require an explicit reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class FigureSpec:
    title: FigureTitle
    series: tuple[FigureSeries, ...] = ()
    empirical_cdf_series: tuple[EmpiricalCdfFigureSeries, ...] = ()
    paired_metric_series: tuple[PairedMetricFigureSeries, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.title, FigureTitle):
            object.__setattr__(self, "title", FigureTitle(self.title))
        if not self.series and not self.empirical_cdf_series and not self.paired_metric_series:
            raise ValueError("figure specifications require at least one series")


def empirical_cdf_series_from_points(
    *,
    label: FigureLabel,
    points: tuple[tuple[MetricValue, MetricValue], ...],
    client_id: ClientIdentityToken | None,
    seed: Seed | None,
    score_role: ScoreRole | None,
    threshold_overlays: tuple[ThresholdOverlay, ...] = (),
    source_checksum: Checksum | None,
    unavailable_reason: AnalysisReasonText | None = None,
) -> EmpiricalCdfFigureSeries:
    if unavailable_reason is not None:
        return EmpiricalCdfFigureSeries(
            label=label,
            x_metric=MetricId.RECONSTRUCTION_ERROR,
            y_metric=MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY,
            availability=AvailabilityStatus.UNAVAILABLE,
            x_values=(),
            y_values=(),
            client_id=client_id,
            seed=seed,
            score_role=score_role,
            threshold_overlays=(),
            source_checksum=source_checksum,
            unavailable_reason=unavailable_reason,
        )
    return EmpiricalCdfFigureSeries(
        label=label,
        x_metric=MetricId.RECONSTRUCTION_ERROR,
        y_metric=MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY,
        availability=AvailabilityStatus.AVAILABLE,
        x_values=tuple(point[0] for point in points),
        y_values=tuple(point[1] for point in points),
        client_id=client_id,
        seed=seed,
        score_role=score_role,
        threshold_overlays=threshold_overlays,
        source_checksum=source_checksum,
        unavailable_reason=None,
    )


def score_geometry_figure(
    geometry: ScoreGeometryResult,
    *,
    title: FigureTitle,
    client_id: ClientIdentityToken | None = None,
) -> FigureSpec:
    """Build one validated empirical-CDF figure from a frozen score-geometry record.

    A client filter is used only for the pre-specified deep-dive panel; callers
    otherwise receive every declared client and score role in the geometry.
    """
    series: list[EmpiricalCdfFigureSeries] = []
    for client_geometry in geometry.clients:
        if client_id is not None and client_geometry.client.client_id != client_id:
            continue
        label = FigureLabel(
            f"seed{geometry.seed.value}:{client_geometry.client.client_id.value}:{client_geometry.score_role.value}"
        )
        overlays = tuple(
            ThresholdOverlay(method=item.method, value=ThresholdValue(item.threshold.value))
            for item in geometry.threshold_overlays
            if item.client is None or item.client == client_geometry.client
        )
        if client_geometry.unavailable_reason is not None:
            series.append(
                empirical_cdf_series_from_points(
                    label=label,
                    points=(),
                    client_id=client_geometry.client.client_id,
                    seed=geometry.seed,
                    score_role=client_geometry.score_role,
                    threshold_overlays=(),
                    source_checksum=geometry.source_score_checksum,
                    unavailable_reason=AnalysisReasonText(client_geometry.unavailable_reason),
                )
            )
            continue
        points = tuple(
            (point.score, MetricValue(point.cumulative_probability.value)) for point in client_geometry.empirical_cdf
        )
        series.append(
            empirical_cdf_series_from_points(
                label=label,
                points=points,
                client_id=client_geometry.client.client_id,
                seed=geometry.seed,
                score_role=client_geometry.score_role,
                threshold_overlays=overlays,
                source_checksum=geometry.source_score_checksum,
            )
        )
    if not series:
        selected = client_id.value if client_id is not None else "all clients"
        raise ValueError(f"score geometry contains no series for {selected}")
    return FigureSpec(title=title, empirical_cdf_series=tuple(series))


def render_markdown_figure(figure: FigureSpec) -> ReportLine:
    """Render every validated figure series as explicit publication evidence."""
    rows = [
        f"### {figure.title}",
        "",
    ]
    if figure.empirical_cdf_series:
        rows.extend(
            [
                (
                    "| Series | X metric | Y metric | Availability | Client | Seed | Role "
                    "| X values | Y values | Threshold overlays | Reason |"
                ),
                "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        rows.extend(_render_empirical_series(series) for series in figure.empirical_cdf_series)
        rows.append("")
    if figure.series:
        rows.extend(
            [
                "| Series | Metric | Availability | Values |",
                "| --- | --- | --- | --- |",
            ]
        )
        rows.extend(_render_series(series) for series in figure.series)
    if figure.paired_metric_series:
        rows.extend(
            [
                "",
                "| Series | X axis | Y axis | Availability | Point labels | X values | Y values | Reason |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        rows.extend(_render_paired_metric_series(series) for series in figure.paired_metric_series)
    return ReportLine("\n".join(rows).rstrip())


def _render_series(series: FigureSeries) -> ReportLine:
    values = ", ".join(format(value.value, ".17g") for value in series.values) if series.values else "—"
    return ReportLine(f"| {series.label} | `{series.metric.value}` | `{series.availability.value}` | {values} |")


def _render_empirical_series(series: EmpiricalCdfFigureSeries) -> ReportLine:
    x_values = ", ".join(format(value.value, ".17g") for value in series.x_values) if series.x_values else "—"
    y_values = ", ".join(format(value.value, ".17g") for value in series.y_values) if series.y_values else "—"
    overlays = (
        ", ".join(
            f"{overlay.method.value}={format(overlay.value.value, '.17g')}" for overlay in series.threshold_overlays
        )
        if series.threshold_overlays
        else "—"
    )
    client = series.client_id.value if series.client_id is not None else "—"
    seed = str(series.seed.value) if series.seed is not None else "—"
    role = series.score_role.value if series.score_role is not None else "—"
    reason = series.unavailable_reason if series.unavailable_reason is not None else "—"
    return ReportLine(
        f"| {series.label} | `{series.x_metric.value}` | `{series.y_metric.value}` | "
        f"`{series.availability.value}` | {client} | {seed} | {role} | {x_values} | {y_values} | "
        f"{overlays} | {reason} |"
    )


def _render_paired_metric_series(series: PairedMetricFigureSeries) -> ReportLine:
    labels = ", ".join(series.point_labels) if series.point_labels else "—"
    x_values = ", ".join(format(value.value, ".17g") for value in series.x_values) if series.x_values else "—"
    y_values = ", ".join(format(value.value, ".17g") for value in series.y_values) if series.y_values else "—"
    reason = series.unavailable_reason if series.unavailable_reason is not None else "—"
    return ReportLine(
        f"| {series.label} | {series.x_label} | {series.y_label} | `{series.availability.value}` | "
        f"{labels} | {x_values} | {y_values} | {reason} |"
    )
