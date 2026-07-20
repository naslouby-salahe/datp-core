"""Streaming CSV source records with deterministic provenance and numeric validation."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterator
from pathlib import Path

from attrs import define


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
        reader = csv.DictReader(source)
        fieldnames = tuple(reader.fieldnames or ())
        missing = tuple(header for header in required_headers if header not in fieldnames)
        if missing:
            raise ValueError(f"Source {path} is missing required headers: {', '.join(missing)}")
        for source_row_index, record in enumerate(reader, start=1):
            values: list[float] = []
            reason: str | None = None
            for header in required_headers:
                raw_value = record[header]
                if raw_value is None or raw_value.strip() == "":
                    reason = f"blank numeric feature '{header}'"
                    break
                try:
                    value = float(raw_value)
                except ValueError:
                    reason = f"unparseable numeric feature '{header}'"
                    break
                if not math.isfinite(value):
                    reason = f"non-finite numeric feature '{header}'"
                    break
                values.append(value)
            if reason is None:
                yield SourceRow(source_path=path, source_row_index=source_row_index, values=tuple(values))
            else:
                yield SourceRowFailure(source_path=path, source_row_index=source_row_index, reason=reason)


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
        reader = csv.DictReader(source)
        fieldnames = tuple(reader.fieldnames or ())
        required_headers = feature_headers + (label_header,)
        missing = tuple(header for header in required_headers if header not in fieldnames)
        if missing:
            raise ValueError(f"Source {path} is missing required headers: {', '.join(missing)}")
        for source_row_index, record in enumerate(reader, start=1):
            if None in record or any(record[header] is None for header in required_headers):
                yield SourceRowFailure(
                    source_path=path,
                    source_row_index=source_row_index,
                    reason="field count differs from configured header",
                )
                continue
            raw_label = record[label_header]
            if raw_label is None or not raw_label.strip():
                yield SourceRowFailure(
                    source_path=path,
                    source_row_index=source_row_index,
                    reason=f"blank categorical label '{label_header}'",
                )
                continue
            values: list[float] = []
            reason: str | None = None
            for header in feature_headers:
                raw_value = record[header]
                if raw_value is None or raw_value.strip() == "":
                    reason = f"blank numeric feature '{header}'"
                    break
                try:
                    value = float(raw_value)
                except ValueError:
                    reason = f"unparseable numeric feature '{header}'"
                    break
                if not math.isfinite(value):
                    reason = f"non-finite numeric feature '{header}'"
                    break
                values.append(value)
            if reason is not None:
                yield SourceRowFailure(source_path=path, source_row_index=source_row_index, reason=reason)
                continue
            yield LabeledSourceRow(
                source_row=SourceRow(source_path=path, source_row_index=source_row_index, values=tuple(values)),
                label=raw_label.strip(),
            )
