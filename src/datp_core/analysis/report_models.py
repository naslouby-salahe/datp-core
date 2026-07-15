from dataclasses import dataclass
from decimal import Decimal
from math import isfinite

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.experiments.protocols import FigureType, TableType

type ReportValue = str | int | float | Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportColumn:
    key: str
    label: str

    def __post_init__(self) -> None:
        if not self.key or not self.key.isidentifier() or not self.label.strip():
            raise DomainValidationError(
                detail="report columns require an identifier key and a non-empty label",
                value=repr(self),
                constraint="identifier key and non-empty label",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ReportRow:
    values: tuple[ReportValue, ...]

    def __post_init__(self) -> None:
        if not _has_valid_report_row_values(self.values):
            raise DomainValidationError(
                detail="report rows require one or more finite scalar values",
                value=repr(self),
                constraint="non-empty tuple[str | int | float | Decimal] without bool or non-finite float",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class TableSpecification:
    table_type: TableType
    columns: tuple[ReportColumn, ...]
    rows: tuple[ReportRow, ...]

    def __post_init__(self) -> None:
        if not _has_valid_table_components(self.table_type, self.columns, self.rows):
            raise DomainValidationError(
                detail="table specifications require one typed kind, unique columns, and rectangular rows",
                value=repr(self),
                constraint="TableType with unique columns and rows matching column count",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class CartesianPoint:
    horizontal: ReportValue
    vertical: ReportValue

    def __post_init__(self) -> None:
        if not _is_report_value(self.horizontal) or not _is_report_value(self.vertical):
            raise DomainValidationError(
                detail="cartesian points require finite scalar coordinates",
                value=repr(self),
                constraint="str | int | finite float | Decimal coordinates",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FigureSeries:
    label: str
    points: tuple[CartesianPoint, ...]

    def __post_init__(self) -> None:
        if not self.label.strip() or not self.points:
            raise DomainValidationError(
                detail="figure series require a non-empty label and one or more points",
                value=repr(self),
                constraint="non-empty label and non-empty tuple[CartesianPoint, ...]",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class SeriesFigureSpecification:
    figure_type: FigureType
    horizontal_label: str
    vertical_label: str
    series: tuple[FigureSeries, ...]

    def __post_init__(self) -> None:
        if not _has_valid_series_figure_components(
            self.figure_type,
            self.horizontal_label,
            self.vertical_label,
            self.series,
        ):
            raise DomainValidationError(
                detail="series figures require a non-heatmap kind, labelled axes, and unique series",
                value=repr(self),
                constraint="non-HEATMAP FigureType with non-empty axes and unique FigureSeries",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class HeatmapCell:
    horizontal: ReportValue
    vertical: ReportValue
    intensity: ReportValue

    def __post_init__(self) -> None:
        if not all(_is_report_value(value) for value in (self.horizontal, self.vertical, self.intensity)):
            raise DomainValidationError(
                detail="heatmap cells require finite scalar coordinates and intensity",
                value=repr(self),
                constraint="str | int | finite float | Decimal coordinates and intensity",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class HeatmapFigureSpecification:
    figure_type: FigureType
    horizontal_label: str
    vertical_label: str
    intensity_label: str
    cells: tuple[HeatmapCell, ...]

    def __post_init__(self) -> None:
        _validate_heatmap_figure(self)


type FigureSpecification = SeriesFigureSpecification | HeatmapFigureSpecification


def _has_valid_report_row_values(values: tuple[ReportValue, ...]) -> bool:
    return bool(values) and all(_is_report_value(value) for value in values)


def _has_valid_table_components(
    table_type: TableType,
    columns: tuple[ReportColumn, ...],
    rows: tuple[ReportRow, ...],
) -> bool:
    return all(
        (
            type(table_type) is TableType,
            bool(columns),
            bool(rows),
            _has_unique_column_keys(columns),
            _has_rectangular_rows(columns, rows),
        )
    )


def _has_unique_column_keys(columns: tuple[ReportColumn, ...]) -> bool:
    return len({column.key for column in columns}) == len(columns)


def _has_rectangular_rows(columns: tuple[ReportColumn, ...], rows: tuple[ReportRow, ...]) -> bool:
    return all(len(row.values) == len(columns) for row in rows)


def _has_valid_series_figure_components(
    figure_type: FigureType,
    horizontal_label: str,
    vertical_label: str,
    series: tuple[FigureSeries, ...],
) -> bool:
    return all(
        (
            type(figure_type) is FigureType,
            figure_type is not FigureType.HEATMAP,
            bool(horizontal_label.strip()),
            bool(vertical_label.strip()),
            bool(series),
            _has_unique_series_labels(series),
        )
    )


def _has_unique_series_labels(series: tuple[FigureSeries, ...]) -> bool:
    return len({item.label for item in series}) == len(series)


def _validate_heatmap_figure(specification: HeatmapFigureSpecification) -> None:
    if not _has_valid_heatmap_figure_components(specification):
        raise DomainValidationError(
            detail="heatmap figures require labelled axes, an intensity label, and one or more cells",
            value=repr(specification),
            constraint="HEATMAP with non-empty labels and non-empty tuple[HeatmapCell, ...]",
        )


def _has_valid_heatmap_figure_components(specification: HeatmapFigureSpecification) -> bool:
    return all(
        (
            specification.figure_type is FigureType.HEATMAP,
            bool(specification.horizontal_label.strip()),
            bool(specification.vertical_label.strip()),
            bool(specification.intensity_label.strip()),
            bool(specification.cells),
        )
    )


def _is_report_value(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, str | int | float | Decimal):
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, float):
        return isfinite(value)
    if isinstance(value, Decimal):
        return value.is_finite()
    return True
