"""CSV streaming and parsing — numeric validation, row failure production."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterator
from pathlib import Path

from datp_core.data.sources.models import (
    CsvValidationResult,
    LabeledSourceRow,
    SourceRow,
    SourceRowFailure,
    SourceRowValidation,
    LabeledSourceRowValidation,
)


def iter_numeric_csv_source(path: Path, required_headers: tuple[str, ...]) -> Iterator[SourceRowValidation]:
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
        if header not in header_to_index:
            return [], f"missing required header '{header}'"
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
