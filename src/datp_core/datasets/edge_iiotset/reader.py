"""Separate lazy readers for audited Edge-IIoTset benign and attack sources."""

from pathlib import Path

import polars as pl

from datp_core.datasets.materialization import provenance_expressions
from datp_core.datasets.models import CanonicalProvenanceColumn

from .schema import (
    EDGE_RAW_COLUMNS,
    EDGE_SCHEMA,
    EdgeCanonicalColumn,
    EdgeRawColumn,
    EdgeSensorGroup,
    benign_sensor_group,
    is_attack_source,
    source_relative_path,
)


class EdgeIIoTsetReader:
    """Preserve mixed raw fields without inferring sensor identity for attacks."""

    def read_benign(self, path: Path) -> pl.LazyFrame:
        sensor_group = benign_sensor_group(path)
        return self._read(path, sensor_group)

    def read_attack(self, path: Path) -> pl.LazyFrame:
        if not is_attack_source(path):
            raise ValueError("unrecognized Edge attack source")
        return self._read(path, None)

    def _read(self, path: Path, sensor_group: EdgeSensorGroup | None) -> pl.LazyFrame:
        source = pl.scan_csv(
            path,
            schema=pl.Schema(tuple((column, pl.String) for column in EDGE_RAW_COLUMNS)),
            try_parse_dates=False,
            null_values=("",),
        )
        if tuple(source.collect_schema().names()) != EDGE_RAW_COLUMNS:
            raise ValueError("Edge source columns differ from the audited order")
        return (
            source.with_row_index(CanonicalProvenanceColumn.SOURCE_ROW_INDEX)
            .with_columns(
                pl.col(EdgeRawColumn.TIMESTAMP).alias(EdgeCanonicalColumn.RAW_TIMESTAMP),
                pl.col(EdgeRawColumn.ATTACK_LABEL).alias(EdgeCanonicalColumn.ATTACK_LABEL),
                pl.col(EdgeRawColumn.ATTACK_TYPE).alias(EdgeCanonicalColumn.ATTACK_TYPE),
                pl.col(CanonicalProvenanceColumn.SOURCE_ROW_INDEX).cast(pl.UInt64),
                pl.lit(None, dtype=pl.Datetime("ns", time_zone="UTC")).alias(EdgeCanonicalColumn.CAPTURE_TIMESTAMP),
                pl.lit(path.parent.name, dtype=pl.String).alias(EdgeCanonicalColumn.SOURCE_FOLDER),
                pl.lit(sensor_group, dtype=pl.String).alias(EdgeCanonicalColumn.BENIGN_SENSOR_GROUP),
                *provenance_expressions(path, source_relative_path),
            )
            .select(tuple(column.name for column in EDGE_SCHEMA.columns))
        )
