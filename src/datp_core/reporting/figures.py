"""Publication figure specifications that cannot invent unavailable series."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.domain.enums import AvailabilityStatus, MetricId


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
class FigureSpec:
    title: str
    series: tuple[FigureSeries, ...]

    def __post_init__(self) -> None:
        if not self.title.strip() or not self.series:
            raise ValueError("figure specifications require a title and series")
