"""Edge-IIoTset CSV source parsing."""

from __future__ import annotations

import csv
import math
from collections.abc import Iterator
from pathlib import Path

from datp_core.data.adapters.edge_iiotset.models import EdgeIIoTsetRow
from datp_core.data.sources.models import SourceRowFailure


def iter_edge_iiotset_source(
    path: Path,
    normal_root: Path,
    attack_root: Path,
    numeric_headers: tuple[str, ...],
    categorical_headers: tuple[str, ...],
    binary_label_header: str,
    multiclass_label_header: str,
    timestamp_header: str | None = None,
) -> Iterator[EdgeIIoTsetRow | SourceRowFailure]:
    try:
        relative_normal = path.relative_to(normal_root)
        client_id: str | None = relative_normal.parts[0] if len(relative_normal.parts) >= 2 else None
        is_attack = False
    except ValueError:
        try:
            path.relative_to(attack_root)
        except ValueError as exc:
            raise ValueError("Edge-IIoTset source path escapes configured normal and attack roots") from exc
        client_id = None
        is_attack = True
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        required = numeric_headers + categorical_headers + (binary_label_header, multiclass_label_header)
        if timestamp_header is not None and timestamp_header not in required:
            required += (timestamp_header,)
        missing = tuple(header for header in required if header not in tuple(reader.fieldnames or ()))
        if missing:
            raise ValueError(f"Source {path} is missing required headers: {', '.join(missing)}")
        for index, record in enumerate(reader, start=1):
            if None in record or any(record[header] is None for header in required):
                yield SourceRowFailure(
                    source_path=path, source_row_index=index, reason="field count differs from configured header"
                )
                continue
            values: list[float] = []
            reason: str | None = None
            for header in numeric_headers:
                raw = record[header]
                try:
                    value = float(int(raw, 16)) if raw.lower().startswith("0x") else float(raw)
                except ValueError:
                    reason = f"invalid retained numeric feature '{header}'"
                    break
                if not math.isfinite(value):
                    reason = f"invalid retained numeric feature '{header}'"
                    break
                values.append(value)
            if reason is not None:
                yield SourceRowFailure(source_path=path, source_row_index=index, reason=reason)
                continue
            binary_label = record[binary_label_header].strip()
            multiclass = record[multiclass_label_header].strip()
            if binary_label not in {"0", "1"} or not multiclass:
                yield SourceRowFailure(
                    source_path=path, source_row_index=index, reason="invalid configured Edge label fields"
                )
                continue
            if is_attack == (binary_label == "0"):
                yield SourceRowFailure(
                    source_path=path,
                    source_row_index=index,
                    reason="source path conflicts with configured Edge binary label",
                )
                continue
            timestamp = None
            if timestamp_header is not None:
                try:
                    timestamp = _time_of_day_seconds(record[timestamp_header])
                except ValueError:
                    yield SourceRowFailure(
                        source_path=path,
                        source_row_index=index,
                        reason=f"invalid temporal ordering field '{timestamp_header}'",
                    )
                    continue
            yield EdgeIIoTsetRow(
                client_id=client_id,
                is_attack=is_attack,
                source_path=path,
                source_row_index=index,
                numeric_values=tuple(values),
                categorical_values=tuple(
                    record[header] if record[header] != "" else None for header in categorical_headers
                ),
                multiclass_label=multiclass,
                time_of_day_seconds=timestamp,
            )


def _time_of_day_seconds(value: str) -> float:
    try:
        time_part = value.strip().split()[-1]
        hours, minutes, seconds = time_part.split(":")
        parsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (IndexError, ValueError) as exc:
        raise ValueError("invalid time-of-day") from exc
    if not math.isfinite(parsed) or not 0.0 <= parsed < 86_400.0:
        raise ValueError("time-of-day is out of range")
    return parsed
