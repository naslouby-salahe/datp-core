from dataclasses import dataclass
from pathlib import Path

import polars as pl

from datp_core.core.numeric import LogicalElementCount, ValidationIssueCount
from datp_core.data.contracts import AggregateCountColumn, CanonicalProvenanceColumn
from datp_core.data.materialization import provenance_expressions

from .schema import (
    NBAIOT_FEATURE_COLUMNS,
    NBAIOT_SCHEMA,
    NBaIoTCanonicalColumn,
    device_family,
    parse_source_identity,
    source_relative_path,
)


@dataclass(frozen=True, slots=True)
class NBaIoTFiniteValueSummary:
    total_rows: LogicalElementCount
    invalid_rows: ValidationIssueCount


class NBaIoTReader:
    def read(self, path: Path) -> pl.LazyFrame:
        source_identity = parse_source_identity(path)
        frame = pl.scan_csv(
            path,
            schema=pl.Schema(tuple((column, pl.Float64) for column in NBAIOT_FEATURE_COLUMNS)),
            try_parse_dates=False,
        )
        observed_columns = tuple(frame.collect_schema().names())
        if observed_columns != NBAIOT_FEATURE_COLUMNS:
            raise ValueError("N-BaIoT source columns differ from the audited order")
        return (
            frame.with_row_index(CanonicalProvenanceColumn.SOURCE_ROW_INDEX)
            .with_columns(
                pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).cast(pl.UInt64),
                pl.lit(source_identity.device, dtype=pl.String).alias(NBaIoTCanonicalColumn.PHYSICAL_CLIENT_ID),
                pl.lit(device_family(source_identity.device), dtype=pl.String).alias(
                    NBaIoTCanonicalColumn.PHYSICAL_DEVICE_FAMILY
                ),
                pl.lit(source_identity.source_label, dtype=pl.String).alias(NBaIoTCanonicalColumn.RAW_LABEL),
                pl.lit(source_identity.attack_family, dtype=pl.String).alias(NBaIoTCanonicalColumn.ATTACK_FAMILY),
                pl.lit(source_identity.attack_subtype, dtype=pl.String).alias(NBaIoTCanonicalColumn.ATTACK_SUBTYPE),
                *provenance_expressions(path, source_relative_path),
            )
            .select(tuple(column.name for column in NBAIOT_SCHEMA.columns))
        )

    def finite_value_summary(self, frame: pl.LazyFrame) -> NBaIoTFiniteValueSummary:
        summary = (
            frame.select(NBAIOT_FEATURE_COLUMNS)
            .select(
                pl.len().alias(AggregateCountColumn.TOTAL_ROWS),
                pl.any_horizontal(tuple(~pl.col(column).is_finite() for column in NBAIOT_FEATURE_COLUMNS)).alias(
                    AggregateCountColumn.INVALID
                ),
            )
            .select(
                pl.len().alias(AggregateCountColumn.TOTAL_ROWS),
                pl.col(AggregateCountColumn.INVALID).sum().alias(AggregateCountColumn.INVALID_ROWS),
            )
            .collect(engine="streaming")
        )
        return NBaIoTFiniteValueSummary(
            total_rows=LogicalElementCount(int(summary.item(0, AggregateCountColumn.TOTAL_ROWS))),
            invalid_rows=ValidationIssueCount(int(summary.item(0, AggregateCountColumn.INVALID_ROWS))),
        )

    def validate_finite_values(self, frame: pl.LazyFrame) -> LogicalElementCount:
        summary = self.finite_value_summary(frame)
        if summary.invalid_rows.value:
            raise ValueError("N-BaIoT contains non-finite feature values")
        return summary.total_rows
