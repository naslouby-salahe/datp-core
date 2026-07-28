"""Single authority for materialized dataset schemas."""

from __future__ import annotations

from pathlib import Path

import msgspec
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from datp_core.core.hashing import Checksum, compute_payload_checksum
from datp_core.data.contracts.enums import (
    DataFailureCode,
    MaterializedArtifactShape,
    MaterializedColumn,
)
from datp_core.data.materialization.errors import DataFailure


class MaterializedSchemaSpec(msgspec.Struct, frozen=True):
    shape: MaterializedArtifactShape
    feature_names: tuple[str, ...]

    @property
    def base_column_names(self) -> tuple[str, ...]:
        common = (
            MaterializedColumn.SPLIT.value,
            MaterializedColumn.CLIENT_ID.value,
            MaterializedColumn.IS_ATTACK.value,
        )
        provenance = (
            MaterializedColumn.SOURCE_PATH.value,
            MaterializedColumn.SOURCE_ROW_INDEX.value,
        )
        if self.shape is MaterializedArtifactShape.CICIOT2023:
            return common + (MaterializedColumn.MULTICLASS_LABEL.value,) + provenance
        if self.shape is MaterializedArtifactShape.NBAIOT:
            return common + (MaterializedColumn.ATTACK_FAMILY.value,) + provenance
        if self.shape is MaterializedArtifactShape.EDGE_BENIGN_TEMPORAL:
            return common + provenance + (MaterializedColumn.CHRONOLOGY_KEY.value,)
        return common + provenance

    @property
    def column_names(self) -> tuple[str, ...]:
        return self.base_column_names + self.feature_names


class SchemaValidation(msgspec.Struct, frozen=True):
    checksum: Checksum
    row_count: int


def validate_materialized_parquet(path: Path, spec: MaterializedSchemaSpec, chunk_row_count: int) -> SchemaValidation:
    parquet_file = pq.ParquetFile(path)
    schema = parquet_file.schema_arrow
    observed_names = tuple(schema.names)
    if observed_names != spec.column_names:
        raise DataFailure(
            DataFailureCode.SCHEMA,
            "materialized schema mismatch; expected "
            + ", ".join(spec.column_names)
            + "; observed "
            + ", ".join(observed_names),
            source_path=path,
            source_row_index=None,
        )
    _validate_types(schema, spec)
    row_count = 0
    non_nullable = tuple(
        name for name in spec.column_names if not _expected_field(name, spec).nullable
    )
    for batch in parquet_file.iter_batches(batch_size=chunk_row_count):
        row_count += batch.num_rows
        for name in non_nullable:
            if batch.column(batch.schema.get_field_index(name)).null_count:
                raise DataFailure(
                    DataFailureCode.SCHEMA,
                    f"materialized column '{name}' contains null values",
                    source_path=path,
                    source_row_index=None,
                )
        for name in spec.feature_names:
            column = batch.column(batch.schema.get_field_index(name))
            finite = pc.all(pc.is_finite(column)).as_py()
            if finite is not True:
                raise DataFailure(
                    DataFailureCode.SCHEMA,
                    f"materialized feature column '{name}' contains a non-finite value",
                    source_path=path,
                    source_row_index=None,
                )
    if row_count == 0:
        raise DataFailure(
            DataFailureCode.SOURCE_EMPTY,
            "materialized dataset is empty",
            source_path=path,
            source_row_index=None,
        )
    checksum = compute_payload_checksum(str(schema).encode("utf-8"))
    return SchemaValidation(checksum=checksum, row_count=row_count)


def _validate_types(schema: pa.Schema, spec: MaterializedSchemaSpec) -> None:
    expected = tuple(_expected_field(name, spec) for name in spec.column_names)
    for observed, required in zip(schema, expected, strict=True):
        if observed.name != required.name or observed.type != required.type:
            raise DataFailure(
                DataFailureCode.SCHEMA,
                f"column '{observed.name}' has type {observed.type}; expected {required.type}",
                source_path=None,
                source_row_index=None,
            )


def _expected_field(name: str, spec: MaterializedSchemaSpec) -> pa.Field:
    if name in spec.feature_names:
        return pa.field(name, pa.float64(), nullable=False)
    if name == MaterializedColumn.IS_ATTACK.value:
        return pa.field(name, pa.bool_(), nullable=False)
    if name in (MaterializedColumn.SOURCE_ROW_INDEX.value, MaterializedColumn.CHRONOLOGY_KEY.value):
        return pa.field(name, pa.int64(), nullable=False)
    nullable = name == MaterializedColumn.ATTACK_FAMILY.value
    return pa.field(name, pa.string(), nullable=nullable)
