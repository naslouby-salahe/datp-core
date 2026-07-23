"""Shared dataset behavior reused by all three adapters: streaming CSV row validation,
split-manifest read/encode, Parquet I/O, and benign-training-row normalization fitting. Genuinely
shared (per section 8.3's "shared behavior must exist once"), unlike a generic dumping-ground
common.py -- every function here is consumed by at least two adapters.
"""

from __future__ import annotations

import csv
import json
import math
from collections.abc import Iterator
from pathlib import Path

import polars as pl
import pyarrow.parquet as pq
from attrs import define

from datp_core.datasets.models import MaterializedSplitEvidence, SplitManifest, SplitManifestEntry, SplitMembership
from datp_core.pipeline.fingerprints import Fingerprint


@define(frozen=True, slots=True, kw_only=True)
class SourceRow:
    """One validated raw source row with immutable source provenance."""

    source_path: Path
    source_row_index: int
    values: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class LabeledSourceRow:
    """One validated numeric source row with a required categorical source label."""

    source_row: SourceRow
    label: str


@define(frozen=True, slots=True, kw_only=True)
class SourceRowFailure:
    """One rejected raw source row; no row is silently discarded."""

    source_path: Path
    source_row_index: int
    reason: str


@define(frozen=True, slots=True, kw_only=True)
class CsvValidationResult:
    """Ordered validated rows and explicit rejection evidence for one source file."""

    rows: tuple[SourceRow, ...]
    failures: tuple[SourceRowFailure, ...]


type SourceRowValidation = SourceRow | SourceRowFailure
type LabeledSourceRowValidation = LabeledSourceRow | SourceRowFailure


def iter_numeric_csv_source(path: Path, required_headers: tuple[str, ...]) -> Iterator[SourceRowValidation]:
    """Yield validated source rows or explicit rejections without retaining a whole file."""
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        raw_headers = next(reader)
        fieldnames = tuple(raw_headers)
        header_to_index = {header: idx for idx, header in enumerate(raw_headers)}
        missing = tuple(header for header in required_headers if header not in fieldnames)
        if missing:
            raise ValueError(f"Source {path} is missing required headers: {', '.join(missing)}")
        for source_row_index, record in enumerate(reader, start=1):
            values, reason = _parse_numeric_row(record, required_headers, header_to_index)
            if reason is None:
                yield SourceRow(source_path=path, source_row_index=source_row_index, values=tuple(values))
            else:
                yield SourceRowFailure(source_path=path, source_row_index=source_row_index, reason=reason)


def _parse_numeric_row(
    record: list[str],
    required_headers: tuple[str, ...],
    header_to_index: dict[str, int],
) -> tuple[list[float], str | None]:
    values: list[float] = []
    for header in required_headers:
        raw_value = record[header_to_index[header]]
        if raw_value is None or raw_value.strip() == "":
            return [], f"blank numeric feature '{header}'"
        try:
            value = float(raw_value)
        except ValueError:
            return [], f"unparseable numeric feature '{header}'"
        if not math.isfinite(value):
            return [], f"non-finite numeric feature '{header}'"
        values.append(value)
    return values, None


def read_numeric_csv_source(path: Path, required_headers: tuple[str, ...]) -> CsvValidationResult:
    """Read one configured CSV source without coercion or silent row loss."""
    rows: list[SourceRow] = []
    failures: list[SourceRowFailure] = []
    for result in iter_numeric_csv_source(path, required_headers):
        if isinstance(result, SourceRow):
            rows.append(result)
        else:
            failures.append(result)
    return CsvValidationResult(rows=tuple(rows), failures=tuple(failures))


def iter_labeled_numeric_csv_source(
    path: Path, feature_headers: tuple[str, ...], label_header: str
) -> Iterator[LabeledSourceRowValidation]:
    """Stream numeric features plus a non-blank label, retaining rejection provenance."""
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        raw_headers = next(reader)
        fieldnames = tuple(raw_headers)
        header_to_index = {header: idx for idx, header in enumerate(raw_headers)}
        required_headers = feature_headers + (label_header,)
        field_count = len(raw_headers)
        missing = tuple(header for header in required_headers if header not in fieldnames)
        if missing:
            raise ValueError(f"Source {path} is missing required headers: {', '.join(missing)}")
        for source_row_index, record in enumerate(reader, start=1):
            if len(record) != field_count:
                yield SourceRowFailure(
                    source_path=path,
                    source_row_index=source_row_index,
                    reason="field count differs from configured header",
                )
                continue
            raw_label = record[header_to_index[label_header]]
            if not raw_label.strip():
                yield SourceRowFailure(
                    source_path=path,
                    source_row_index=source_row_index,
                    reason=f"blank categorical label '{label_header}'",
                )
                continue
            values, reason = _parse_numeric_row(record, feature_headers, header_to_index)
            if reason is not None:
                yield SourceRowFailure(source_path=path, source_row_index=source_row_index, reason=reason)
                continue
            yield LabeledSourceRow(
                source_row=SourceRow(source_path=path, source_row_index=source_row_index, values=tuple(values)),
                label=raw_label.strip(),
            )


def read_materialized_split_evidence(path: str, minimum_benign_calibration_count: int) -> MaterializedSplitEvidence:
    """Extract the materialized schema and validate its row-level split contract."""
    parquet = pq.ParquetFile(path)
    schema = parquet.schema_arrow
    columns = ["split", "client_id", "is_attack", "source_path", "source_row_index"]
    if "chronology_key" in schema.names:
        columns.append("chronology_key")
    table = parquet.read(columns=columns)
    rows = table.to_pylist()
    manifest = SplitManifest(
        entries=tuple(
            SplitManifestEntry(
                source_path=str(row["source_path"]),
                source_row_index=int(row["source_row_index"]),
                client_id=str(row["client_id"]),
                membership=SplitMembership(str(row["split"])),
                is_attack=bool(row["is_attack"]),
                chronology_key=None if "chronology_key" not in row else int(row["chronology_key"]),
            )
            for row in rows
        ),
        minimum_benign_calibration_count=minimum_benign_calibration_count,
    )
    return MaterializedSplitEvidence(
        manifest=manifest,
        schema_columns=tuple((field.name, str(field.type)) for field in schema),
    )


def encode_split_manifest(manifest: SplitManifest) -> bytes:
    """Encode the complete row membership and derived evidence deterministically."""
    return json.dumps(
        {
            "schema_version": 1,
            "minimum_benign_calibration_count": manifest.minimum_benign_calibration_count,
            "entries": [
                {
                    "source_path": entry.source_path,
                    "source_row_index": entry.source_row_index,
                    "client_id": entry.client_id,
                    "membership": entry.membership.value,
                    "is_attack": entry.is_attack,
                    "chronology_key": entry.chronology_key,
                }
                for entry in manifest.entries
            ],
            "split_counts": manifest.split_counts,
            "class_counts": manifest.class_counts,
            "client_row_counts": manifest.client_row_counts,
            "eligible_client_ids": manifest.eligible_client_ids,
            "ineligible_client_ids": manifest.ineligible_client_ids,
        },
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


@define(frozen=True, slots=True, kw_only=True)
class NormalizationFeatureStatistics:
    feature: str
    location: float
    scale: float

    def as_projection(self) -> dict[str, float | str]:
        return {"feature": self.feature, "location": self.location, "scale": self.scale}


@define(frozen=True, slots=True, kw_only=True)
class NormalizationScopeStatistics:
    client_id: str | None
    features: tuple[NormalizationFeatureStatistics, ...]

    def as_projection(self) -> dict[str, object]:
        return {
            "client_id": self.client_id,
            "features": [feature.as_projection() for feature in self.features],
        }


@define(frozen=True, slots=True, kw_only=True)
class NormalizationEvidence:
    strategy: str
    scope: str
    feature_columns: tuple[str, ...]
    fitted_statistics: tuple[NormalizationScopeStatistics, ...]

    def encode(self) -> bytes:
        return json.dumps(
            {
                "schema_version": 1,
                "strategy": self.strategy,
                "scope": self.scope,
                "feature_columns": self.feature_columns,
                "fitted_statistics": [statistics.as_projection() for statistics in self.fitted_statistics],
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")


def write_dataframe_parquet(
    df: pl.DataFrame,
    target_path: Path,
    scientific_fingerprint: Fingerprint | None = None,
    compression: str = "zstd",
) -> None:
    """Write Polars DataFrame to Parquet with PyArrow schema validation and metadata injection."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    sorted_df = df.select(sorted(df.columns))
    arrow_table = sorted_df.to_arrow()

    existing_meta = arrow_table.schema.metadata or {}
    custom_meta = {
        b"schema_version": b"1",
        b"datp_fingerprint": (scientific_fingerprint.value.encode("utf-8") if scientific_fingerprint else b"none"),
    }
    merged_meta = {**existing_meta, **custom_meta}
    arrow_table = arrow_table.replace_schema_metadata(merged_meta)

    pq.write_table(arrow_table, target_path, compression=compression)


def read_dataframe_parquet(target_path: Path) -> pl.DataFrame:
    """Read Parquet file into Polars DataFrame with existence check."""
    if not target_path.exists():
        raise FileNotFoundError(f"Parquet file not found: {target_path}")
    return pl.read_parquet(target_path)


def inspect_parquet_schema(target_path: Path) -> dict[str, str]:
    """Inspect PyArrow Parquet schema column types."""
    schema = pq.read_schema(target_path)
    return {name: str(dtype) for name, dtype in zip(schema.names, schema.types, strict=False)}


def normalize_materialized_parquet(
    source_path: Path,
    target_path: Path,
    *,
    feature_columns: tuple[str, ...],
    strategy: str,
    scope: str,
) -> NormalizationEvidence:
    """Fit configured normalization on benign training rows, then transform every materialized row."""
    if strategy not in {"min_max", "standard"}:
        raise ValueError(f"Unsupported normalization strategy: {strategy}")
    if scope not in {"global_train", "per_client_train"}:
        raise ValueError(f"Unsupported normalization fit scope: {scope}")
    if not feature_columns:
        raise ValueError("Normalization requires at least one configured feature column")

    source = pl.scan_parquet(source_path).with_row_index("__datp_row_order")
    available_columns = set(source.collect_schema().names())
    required_columns = {"split", "is_attack", *feature_columns}
    if scope == "per_client_train":
        required_columns.add("client_id")
    missing_columns = sorted(required_columns - available_columns)
    if missing_columns:
        raise ValueError(f"Materialized payload is missing normalization columns: {', '.join(missing_columns)}")

    train = source.filter((pl.col("split") == "train") & ~pl.col("is_attack"))
    statistics = _normalization_statistics(train, feature_columns, strategy, scope)
    if statistics.height == 0:
        raise ValueError("Normalization requires benign training rows")
    if scope == "per_client_train":
        observed_clients = set(source.select("client_id").unique().collect()["client_id"].to_list())
        fitted_clients = set(statistics["client_id"].to_list())
        missing_clients = sorted(observed_clients - fitted_clients)
        if missing_clients:
            raise ValueError(f"Normalization lacks benign training rows for clients: {', '.join(missing_clients)}")
        transformed = source.join(statistics.lazy(), on="client_id", how="left")
    else:
        transformed = source.join(statistics.lazy(), how="cross")
    transformed = transformed.with_columns(_normalization_expressions(feature_columns, strategy))
    transformed = transformed.sort("__datp_row_order").drop(
        "__datp_row_order", *_normalization_statistic_columns(feature_columns)
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)
    transformed.sink_parquet(target_path, compression="zstd")
    return NormalizationEvidence(
        strategy=strategy,
        scope=scope,
        feature_columns=feature_columns,
        fitted_statistics=_normalization_evidence_statistics(statistics, feature_columns, scope),
    )


def _normalization_statistics(
    train: pl.LazyFrame, feature_columns: tuple[str, ...], strategy: str, scope: str
) -> pl.DataFrame:
    aggregations = [
        expression.alias(f"__datp_{name}_{column}")
        for column in feature_columns
        for name, expression in (
            ("location", pl.col(column).min() if strategy == "min_max" else pl.col(column).mean()),
            ("scale", pl.col(column).max() if strategy == "min_max" else pl.col(column).std(ddof=0)),
        )
    ]
    return (
        train.group_by("client_id").agg(aggregations).collect()
        if scope == "per_client_train"
        else train.select(aggregations).collect()
    )


def _normalization_evidence_statistics(
    statistics: pl.DataFrame, feature_columns: tuple[str, ...], scope: str
) -> tuple[NormalizationScopeStatistics, ...]:
    return tuple(
        NormalizationScopeStatistics(
            client_id=str(row["client_id"]) if scope == "per_client_train" else None,
            features=tuple(
                NormalizationFeatureStatistics(
                    feature=column,
                    location=float(row[f"__datp_location_{column}"]),
                    scale=float(row[f"__datp_scale_{column}"]),
                )
                for column in feature_columns
            ),
        )
        for row in statistics.iter_rows(named=True)
    )


def _normalization_expressions(feature_columns: tuple[str, ...], strategy: str) -> list[pl.Expr]:
    expressions: list[pl.Expr] = []
    for column in feature_columns:
        location = pl.col(f"__datp_location_{column}")
        scale = pl.col(f"__datp_scale_{column}")
        denominator = scale - location if strategy == "min_max" else scale
        expressions.append(
            pl.when(denominator == 0.0).then(0.0).otherwise((pl.col(column) - location) / denominator).alias(column)
        )
    return expressions


def _normalization_statistic_columns(feature_columns: tuple[str, ...]) -> list[str]:
    return [f"__datp_{name}_{column}" for column in feature_columns for name in ("location", "scale")]
