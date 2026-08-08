"""Publication figure specifications that cannot invent unavailable series."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import AvailabilityStatus, MetricId
from datp_core.core.numeric import MetricValue, Seed


@dataclass(frozen=True, slots=True, kw_only=True)
class FigureSeries:
    label: str
    metric: MetricId
    availability: AvailabilityStatus
    values: tuple[float, ...]

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("figure series require a label")
        if self.availability is not AvailabilityStatus.AVAILABLE and self.values:
            raise ValueError("unavailable figure series cannot contain values")
        if self.availability is AvailabilityStatus.AVAILABLE and not self.values:
            raise ValueError("available figure series require values")


@dataclass(frozen=True, slots=True, kw_only=True)
class EmpiricalCdfFigureSeries:
    """Typed empirical CDF series: x = reconstruction score, y = cumulative probability."""

    label: str
    x_metric: MetricId
    y_metric: MetricId
    availability: AvailabilityStatus
    x_values: tuple[float, ...]
    y_values: tuple[float, ...]
    client_id: str | None
    seed: Seed | None
    score_role: str | None
    threshold_overlays: tuple[tuple[str, float], ...]
    source_checksum: Checksum | None
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("empirical CDF series require a label")
        if self.x_metric is not MetricId.RECONSTRUCTION_ERROR and self.availability is AvailabilityStatus.AVAILABLE:
            raise ValueError("empirical reconstruction CDF series must use reconstruction-error x metric")
        if (
            self.y_metric is not MetricId.EMPIRICAL_CUMULATIVE_PROBABILITY
            and self.availability is AvailabilityStatus.AVAILABLE
        ):
            raise ValueError("empirical CDF series must use cumulative-probability y metric")
        if self.availability is AvailabilityStatus.AVAILABLE:
            if not self.x_values or not self.y_values:
                raise ValueError("available empirical CDF series require x and y values")
            if len(self.x_values) != len(self.y_values):
                raise ValueError("empirical CDF x and y values must have equal length")
            if any(not (0.0 < y <= 1.0) for y in self.y_values):
                raise ValueError("empirical CDF y values must lie in (0, 1]")
            if any(left > right for left, right in zip(self.y_values, self.y_values[1:], strict=False)):
                raise ValueError("empirical CDF y values must be nondecreasing")
            if self.unavailable_reason is not None:
                raise ValueError("available empirical CDF series cannot carry an unavailable reason")
        else:
            if self.x_values or self.y_values:
                raise ValueError("unavailable empirical CDF series cannot contain values")
            if self.unavailable_reason is None:
                raise ValueError("unavailable empirical CDF series require an explicit reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class FigureSpec:
    title: str
    series: tuple[FigureSeries, ...] = ()
    empirical_cdf_series: tuple[EmpiricalCdfFigureSeries, ...] = ()

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("figure specifications require a title")
        if not self.series and not self.empirical_cdf_series:
            raise ValueError("figure specifications require at least one series")


def empirical_cdf_series_from_points(
    *,
    label: str,
    points: tuple[tuple[MetricValue, MetricValue], ...],
    client_id: str | None,
    seed: Seed | None,
    score_role: str | None,
    threshold_overlays: tuple[tuple[str, float], ...] = (),
    source_checksum: Checksum | None,
    unavailable_reason: str | None = None,
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
        x_values=tuple(point[0].value for point in points),
        y_values=tuple(point[1].value for point in points),
        client_id=client_id,
        seed=seed,
        score_role=score_role,
        threshold_overlays=threshold_overlays,
        source_checksum=source_checksum,
        unavailable_reason=None,
    )


def render_markdown_figure(figure: FigureSpec) -> str:
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
    return "\n".join(rows).rstrip()


def _render_series(series: FigureSeries) -> str:
    values = ", ".join(format(value, ".17g") for value in series.values) if series.values else "—"
    return f"| {series.label} | `{series.metric.value}` | `{series.availability.value}` | {values} |"


def _render_empirical_series(series: EmpiricalCdfFigureSeries) -> str:
    x_values = ", ".join(format(value, ".17g") for value in series.x_values) if series.x_values else "—"
    y_values = ", ".join(format(value, ".17g") for value in series.y_values) if series.y_values else "—"
    overlays = (
        ", ".join(f"{label}={format(value, '.17g')}" for label, value in series.threshold_overlays)
        if series.threshold_overlays
        else "—"
    )
    client = series.client_id if series.client_id is not None else "—"
    seed = str(series.seed.value) if series.seed is not None else "—"
    role = series.score_role if series.score_role is not None else "—"
    reason = series.unavailable_reason if series.unavailable_reason is not None else "—"
    return (
        f"| {series.label} | `{series.x_metric.value}` | `{series.y_metric.value}` | "
        f"`{series.availability.value}` | {client} | {seed} | {role} | {x_values} | {y_values} | "
        f"{overlays} | {reason} |"
    )
