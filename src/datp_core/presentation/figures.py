from __future__ import annotations

from dataclasses import dataclass

from datp_core.analysis.contrasts import PairedContrasts
from datp_core.analysis.descriptive import ScoreGeometryResult, ScoreRole
from datp_core.analysis.inference.bootstrap.contracts import BootstrapInterval
from datp_core.analysis.mechanisms.equity_pareto import EquityUtilityParetoView
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
    benign_exceedance: MetricValue | None = None
    attack_acceptance: MetricValue | None = None
    balanced_accuracy: MetricValue | None = None
    macro_f1: MetricValue | None = None


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


def equity_utility_pareto_figure(
    view: EquityUtilityParetoView,
    *,
    title: FigureTitle,
) -> FigureSpec:
    """Preserve Pareto means and every seed-level point in a publication figure source."""

    mean_series = PairedMetricFigureSeries(
        label=FigureLabel("method arithmetic means; Pareto membership uses these coordinates"),
        x_label=FigureLabel("mean seed-level CV(FPR), lower is better"),
        y_label=FigureLabel(f"mean seed-level {view.utility_metric.value}, higher is better"),
        availability=AvailabilityStatus.AVAILABLE,
        x_values=tuple(point.mean_x for point in view.points),
        y_values=tuple(point.mean_y for point in view.points),
        point_labels=tuple(
            FigureLabel(
                f"{_pareto_policy_label(point.threshold_method.value, point.shrinkage_weight.value)}; "
                f"nondominated={point.nondominated}"
                if point.shrinkage_weight is not None
                else f"{point.threshold_method.value}; nondominated={point.nondominated}"
            )
            for point in view.points
        ),
    )
    seed_series = tuple(
        PairedMetricFigureSeries(
            label=FigureLabel(
                f"{_pareto_policy_label(point.threshold_method.value, point.shrinkage_weight.value)} seed-level points"
                if point.shrinkage_weight is not None
                else f"{point.threshold_method.value} seed-level points"
            ),
            x_label=FigureLabel("CV(FPR), lower is better"),
            y_label=FigureLabel(f"{view.utility_metric.value}, higher is better"),
            availability=AvailabilityStatus.AVAILABLE,
            x_values=point.seed_values_x,
            y_values=point.seed_values_y,
        )
        for point in view.points
    )
    return FigureSpec(title=title, paired_metric_series=(mean_series, *seed_series))


def confirmatory_paired_effect_figure(
    contrasts: PairedContrasts,
    interval: BootstrapInterval,
) -> FigureSpec:
    seed_values = tuple(MetricValue(contrast.seed.value) for contrast in contrasts.ordered_by_seed().values)
    deltas = tuple(contrast.delta for contrast in contrasts.ordered_by_seed().values)
    labels = tuple(FigureLabel(f"seed {contrast.seed.value}") for contrast in contrasts.ordered_by_seed().values)
    if interval.point_estimate is None:
        raise ValueError("confirmatory paired-effect figure requires a point estimate")
    mean = interval.point_estimate
    mean_series = PairedMetricFigureSeries(
        label=FigureLabel("arithmetic mean paired effect"),
        x_label=FigureLabel("training seed"),
        y_label=FigureLabel("mean Delta = CV(FPR) shared minus local"),
        availability=AvailabilityStatus.AVAILABLE,
        x_values=seed_values,
        y_values=tuple(mean for _ in seed_values),
    )
    zero_reference_series = PairedMetricFigureSeries(
        label=FigureLabel("horizontal zero reference"),
        x_label=FigureLabel("training seed"),
        y_label=FigureLabel("Delta = CV(FPR) shared minus local"),
        availability=AvailabilityStatus.AVAILABLE,
        x_values=seed_values,
        y_values=tuple(MetricValue(0.0) for _ in seed_values),
    )
    interval_series = (
        (
            PairedMetricFigureSeries(
                label=FigureLabel("locked 95% BCa interval"),
                x_label=FigureLabel("lower / upper bound"),
                y_label=FigureLabel("Delta"),
                availability=AvailabilityStatus.AVAILABLE,
                x_values=(MetricValue(0.0), MetricValue(1.0)),
                y_values=(interval.lower_bound, interval.upper_bound),
                point_labels=(FigureLabel("lower"), FigureLabel("upper")),
            ),
        )
        if interval.lower_bound is not None and interval.upper_bound is not None
        else ()
    )
    return FigureSpec(
        title=FigureTitle("FIGURE-002 — Confirmatory paired seed-level CV(FPR) effect"),
        paired_metric_series=(
            PairedMetricFigureSeries(
                label=FigureLabel("seed-level paired deltas; zero reference=0"),
                x_label=FigureLabel("training seed"),
                y_label=FigureLabel("Delta = CV(FPR) shared minus local"),
                availability=AvailabilityStatus.AVAILABLE,
                x_values=seed_values,
                y_values=deltas,
                point_labels=labels,
            ),
            zero_reference_series,
            mean_series,
            *interval_series,
        ),
    )


def causal_intervention_map_figure() -> FigureSpec:
    return FigureSpec(
        title=FigureTitle("FIGURE-001 — Causal intervention map and fixed-score boundary"),
        causal_map_lines=tuple(
            FigureLabel(line)
            for line in (
                "raw records -> population / split identity -> fitted preprocessing state -> federated training",
                "-> terminal detector -> canonical calibration + evaluation score artifacts",
                "-> [FIXED-SCORE BOUNDARY] -> threshold estimator -> threshold-calibration scope",
                "-> deployed threshold(s) -> held-out predictions -> per-client metrics",
                "-> cross-client operating-point metrics",
                "preprocessing sensitivity -> fitted preprocessing / detector geometry",
                "FedProx + local fine-tuning + Ditto -> training / detector geometry",
                "Komadina-style estimator axis + q95-vs-moment sensitivity -> threshold estimator",
                "DATP core ladder -> threshold-calibration scope ONLY",
                "one-shot recalibration -> calibration evidence at a later genuine-time window",
                "No arrow from held-out labels or metrics feeds back into estimation, q selection, preprocessing,",
                "training, cluster count, shrinkage, or eligibility.",
            )
        ),
    )


def _pareto_policy_label(method: str, shrinkage_weight: float) -> str:
    return f"{method}(lambda={shrinkage_weight:g})"


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
    causal_map_lines: tuple[FigureLabel, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.title, FigureTitle):
            object.__setattr__(self, "title", FigureTitle(self.title))
        if not (
            self.series or self.empirical_cdf_series or self.paired_metric_series or self.causal_map_lines
        ):
            raise ValueError("figure specifications require at least one series")


def empirical_cdf_series_from_points(
    *,
    label: FigureLabel,
    points: tuple[tuple[MetricValue, MetricValue], ...],
    client_id: ClientIdentityToken | None,
    seed: Seed | None,
    score_role: ScoreRole | None,
    threshold_overlays: tuple[ThresholdOverlay, ...] = (),
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
        unavailable_reason=None,
    )


def score_geometry_figure(
    geometry: ScoreGeometryResult,
    *,
    title: FigureTitle,
    client_id: ClientIdentityToken | None = None,
) -> FigureSpec:

    series: list[EmpiricalCdfFigureSeries] = []
    for client_geometry in geometry.clients:
        if client_id is not None and client_geometry.client.client_id != client_id:
            continue
        label = FigureLabel(
            f"seed{geometry.seed.value}:{client_geometry.client.client_id.value}:{client_geometry.score_role.value}"
        )
        overlays = tuple(
            ThresholdOverlay(
                method=item.method,
                value=ThresholdValue(item.threshold.value),
                benign_exceedance=item.benign_exceedance,
                attack_acceptance=item.attack_acceptance,
                balanced_accuracy=item.balanced_accuracy,
                macro_f1=item.macro_f1,
            )
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
            )
        )
    if not series:
        selected = client_id.value if client_id is not None else "all clients"
        raise ValueError(f"score geometry contains no series for {selected}")
    return FigureSpec(title=title, empirical_cdf_series=tuple(series))


def render_markdown_figure(figure: FigureSpec) -> ReportLine:

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
    if figure.causal_map_lines:
        rows.extend(("", "```text", *figure.causal_map_lines, "```"))
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
            _render_threshold_overlay(overlay) for overlay in series.threshold_overlays
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


def _render_threshold_overlay(overlay: ThresholdOverlay) -> str:
    metrics = (
        ("benign_exceedance", overlay.benign_exceedance),
        ("attack_acceptance", overlay.attack_acceptance),
        ("balanced_accuracy", overlay.balanced_accuracy),
        ("macro_f1", overlay.macro_f1),
    )
    rendered_metrics = ",".join(
        f"{name}={format(value.value, '.17g')}" if value is not None else f"{name}=unavailable"
        for name, value in metrics
    )
    return f"{overlay.method.value}={format(overlay.value.value, '.17g')} ({rendered_metrics})"


def _render_paired_metric_series(series: PairedMetricFigureSeries) -> ReportLine:
    labels = ", ".join(series.point_labels) if series.point_labels else "—"
    x_values = ", ".join(format(value.value, ".17g") for value in series.x_values) if series.x_values else "—"
    y_values = ", ".join(format(value.value, ".17g") for value in series.y_values) if series.y_values else "—"
    reason = series.unavailable_reason if series.unavailable_reason is not None else "—"
    return ReportLine(
        f"| {series.label} | {series.x_label} | {series.y_label} | `{series.availability.value}` | "
        f"{labels} | {x_values} | {y_values} | {reason} |"
    )
