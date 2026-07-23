"""Edge-IIoTset configured benign-client identity and strict numeric parsing."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sqlite3
import struct
from collections.abc import Iterator, Mapping
from io import BytesIO
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory

import pyarrow as pa
import pyarrow.parquet as pq
from attrs import define

from datp_core.datasets.common import SourceRowFailure
from datp_core.datasets.materialization import SourceInventory
from datp_core.datasets.models import (
    AdapterKind,
    CategoricalEncodingRecord,
    DatasetMaterialization,
    DatasetSetup,
    PartitionSeedContract,
    ResolvedDataset,
)
from datp_core.experiments.models import SweepConditionRecord


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetRow:
    client_id: str | None
    is_attack: bool
    source_path: Path
    source_row_index: int
    numeric_values: tuple[float, ...]
    categorical_values: tuple[str | None, ...]
    multiclass_label: str
    time_of_day_seconds: float | None = None


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetSplitRows:
    train: tuple[EdgeIIoTsetRow, ...]
    calibration: tuple[EdgeIIoTsetRow, ...]
    test: tuple[EdgeIIoTsetRow, ...]
    unassigned_attack: tuple[EdgeIIoTsetRow, ...]
    duplicate_rows_removed: int
    recalibration_reference: tuple[EdgeIIoTsetRow, ...] = ()


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetVocabulary:
    categories_by_column: tuple[tuple[str, tuple[str, ...]], ...]


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetNormalization:
    minimums: tuple[float, ...]
    maximums: tuple[float, ...]


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetExternalIndexReport:
    source_rows_seen: int
    excluded_rows: int
    canonical_rows: int


@define(frozen=True, slots=True, kw_only=True)
class EdgeTimestampedRow:
    row: EdgeIIoTsetRow
    time_of_day_seconds: float


@define(frozen=True, slots=True, kw_only=True)
class EdgeChronologicalSplitRows:
    historical_train: tuple[EdgeIIoTsetRow, ...]
    historical_calibration: tuple[EdgeIIoTsetRow, ...]
    future_recalibration: tuple[EdgeIIoTsetRow, ...]
    future_evaluation: tuple[EdgeIIoTsetRow, ...]
    excluded_clients: tuple[str, ...]


type EdgeIIoTsetSourceResult = EdgeIIoTsetRow | SourceRowFailure


def iter_edge_iiotset_source(
    path: Path,
    normal_root: Path,
    attack_root: Path,
    numeric_headers: tuple[str, ...],
    categorical_headers: tuple[str, ...],
    binary_label_header: str,
    multiclass_label_header: str,
    timestamp_header: str | None = None,
) -> Iterator[EdgeIIoTsetSourceResult]:
    """Read one configured Edge source; only normal-group rows receive client identities."""
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


def split_edge_benign_rows(
    rows: tuple[EdgeIIoTsetRow, ...], materialization: DatasetMaterialization
) -> EdgeIIoTsetSplitRows:
    """Deduplicate and split valid folder-defined benign clients; never assign attacks to clients."""
    if materialization.split_method != "random_fractional" or materialization.split_seed is None:
        raise ValueError("Edge-IIoTset benign materialization requires configured random_fractional split and seed")
    train_ratio = float(materialization.ratio("train"))
    calibration_ratio = float(materialization.ratio("calibration"))
    recalibration_ratio = (
        float(materialization.ratio("recalibration_reference"))
        if any(role == "recalibration_reference" for role, _ in materialization.split_ratios)
        else 0.0
    )
    test_ratio = float(materialization.ratio("test"))
    if not math.isclose(
        train_ratio + calibration_ratio + recalibration_ratio + test_ratio, 1.0, rel_tol=0.0, abs_tol=1.0e-12
    ):
        raise ValueError("Edge-IIoTset split ratios must sum exactly to one")
    attacks = tuple(row for row in rows if row.is_attack)
    benign_by_client: dict[str, list[EdgeIIoTsetRow]] = {}
    for row in rows:
        if row.is_attack:
            continue
        if row.client_id is None:
            raise ValueError("Edge-IIoTset benign rows require a configured normal-group client identity")
        benign_by_client.setdefault(row.client_id, []).append(row)
    train: list[EdgeIIoTsetRow] = []
    calibration: list[EdgeIIoTsetRow] = []
    recalibration_reference: list[EdgeIIoTsetRow] = []
    test: list[EdgeIIoTsetRow] = []
    duplicates = 0
    for client_id, client_rows in sorted(benign_by_client.items()):
        canonical: dict[tuple[tuple[float, ...], tuple[str | None, ...]], EdgeIIoTsetRow] = {}
        for row in sorted(client_rows, key=_provenance_key):
            key = (row.numeric_values, row.categorical_values)
            if key in canonical:
                duplicates += 1
            else:
                canonical[key] = row
        ordered = sorted(canonical.values(), key=_edge_content_hash)
        generator = Random(f"{materialization.split_seed.value}:{client_id}")
        for row in ordered:
            draw = generator.random()
            if draw < train_ratio:
                train.append(row)
            elif draw < train_ratio + calibration_ratio:
                calibration.append(row)
            elif draw < train_ratio + calibration_ratio + recalibration_ratio:
                recalibration_reference.append(row)
            else:
                test.append(row)
    return EdgeIIoTsetSplitRows(
        train=tuple(sorted(train, key=_provenance_key)),
        calibration=tuple(sorted(calibration, key=_provenance_key)),
        test=tuple(sorted(test, key=_provenance_key)),
        unassigned_attack=attacks,
        duplicate_rows_removed=duplicates,
        recalibration_reference=tuple(sorted(recalibration_reference, key=_provenance_key)),
    )


def fit_edge_vocabulary(
    train_rows: tuple[EdgeIIoTsetRow, ...], categorical_headers: tuple[str, ...]
) -> EdgeIIoTsetVocabulary:
    """Fit sorted categorical vocabularies exclusively from benign training rows."""
    if any(row.is_attack for row in train_rows):
        raise ValueError("Edge-IIoTset categorical vocabulary may only fit benign training rows")
    values: list[set[str]] = [set() for _ in categorical_headers]
    for row in train_rows:
        if len(row.categorical_values) != len(categorical_headers):
            raise ValueError("Edge-IIoTset categorical row width differs from configured schema")
        for index, value in enumerate(row.categorical_values):
            if value is not None:
                values[index].add(value)
    return EdgeIIoTsetVocabulary(
        categories_by_column=tuple(
            (header, tuple(sorted(values[index]))) for index, header in enumerate(categorical_headers)
        )
    )


def fit_edge_train_normalization(train_rows: tuple[EdgeIIoTsetRow, ...]) -> EdgeIIoTsetNormalization:
    """Fit min/max scalers only from benign training numeric features."""
    if not train_rows or any(row.is_attack for row in train_rows):
        raise ValueError("Edge-IIoTset normalization requires non-empty benign training rows")
    width = len(train_rows[0].numeric_values)
    if any(len(row.numeric_values) != width for row in train_rows):
        raise ValueError("Edge-IIoTset numeric row width differs within training population")
    return EdgeIIoTsetNormalization(
        minimums=tuple(min(row.numeric_values[i] for row in train_rows) for i in range(width)),
        maximums=tuple(max(row.numeric_values[i] for row in train_rows) for i in range(width)),
    )


def encode_edge_split_as_parquet(
    split: EdgeIIoTsetSplitRows,
    numeric_headers: tuple[str, ...],
    vocabulary: EdgeIIoTsetVocabulary,
    normalization: EdgeIIoTsetNormalization,
) -> bytes:
    """Encode a frozen, train-fit benign Edge feature artifact."""
    roles = (
        (("train", split.train), ("calibration", split.calibration))
        + (("recalibration_reference", split.recalibration_reference),)
        if split.recalibration_reference
        else (("train", split.train), ("calibration", split.calibration))
    ) + (("test", split.test),)
    return _encode_edge_roles_as_parquet(
        roles,
        numeric_headers,
        vocabulary,
        normalization,
        chronological=False,
    )


def encode_edge_chronological_split_as_parquet(
    split: EdgeChronologicalSplitRows,
    numeric_headers: tuple[str, ...],
    vocabulary: EdgeIIoTsetVocabulary,
    normalization: EdgeIIoTsetNormalization,
) -> bytes:
    """Encode a chronology-preserving Edge artifact with stable source-order evidence."""
    return _encode_edge_roles_as_parquet(
        (
            ("historical_training", split.historical_train),
            ("historical_calibration", split.historical_calibration),
            ("future_recalibration", split.future_recalibration),
            ("future_evaluation", split.future_evaluation),
        ),
        numeric_headers,
        vocabulary,
        normalization,
        chronological=True,
    )


def _encode_edge_roles_as_parquet(
    roles: tuple[tuple[str, tuple[EdgeIIoTsetRow, ...]], ...],
    numeric_headers: tuple[str, ...],
    vocabulary: EdgeIIoTsetVocabulary,
    normalization: EdgeIIoTsetNormalization,
    *,
    chronological: bool,
) -> bytes:
    category_columns = dict(vocabulary.categories_by_column)
    categorical_headers = tuple(category_columns)
    if len(normalization.minimums) != len(numeric_headers) or len(normalization.maximums) != len(numeric_headers):
        raise ValueError("Edge-IIoTset normalization width differs from numeric schema")
    encoded_headers = list(numeric_headers)
    for header in categorical_headers:
        encoded_headers += [f"{header}={value}" for value in (*category_columns[header], "__MISSING__", "__UNKNOWN__")]
    records: dict[str, list[object]] = {
        "split": [],
        "client_id": [],
        "source_path": [],
        "source_row_index": [],
        "is_attack": [],
    }
    if chronological:
        records["chronology_key"] = []
    records.update({header: [] for header in encoded_headers})
    chronology_key = 0
    for role, rows in roles:
        for row in rows:
            if row.is_attack or row.client_id is None:
                raise ValueError("Edge-IIoTset client artifact may only contain benign assigned rows")
            records["split"].append(role)
            records["client_id"].append(row.client_id)
            records["source_path"].append(row.source_path.as_posix())
            records["source_row_index"].append(row.source_row_index)
            records["is_attack"].append(False)
            if chronological:
                records["chronology_key"].append(chronology_key)
                chronology_key += 1
            for i, header in enumerate(numeric_headers):
                low, high = normalization.minimums[i], normalization.maximums[i]
                records[header].append(0.0 if high == low else (row.numeric_values[i] - low) / (high - low))
            for i, header in enumerate(categorical_headers):
                value = row.categorical_values[i]
                selected = _category_value(value, category_columns[header])
                for category in (*category_columns[header], "__MISSING__", "__UNKNOWN__"):
                    records[f"{header}={category}"].append(float(category == selected))
    payload = BytesIO()
    pq.write_table(pa.table(records), payload, compression="zstd", use_dictionary=False)
    return payload.getvalue()


def index_edge_benign_sources(
    source_paths: tuple[Path, ...],
    normal_root: Path,
    attack_root: Path,
    numeric_headers: tuple[str, ...],
    categorical_headers: tuple[str, ...],
    binary_label_header: str,
    multiclass_label_header: str,
) -> EdgeIIoTsetExternalIndexReport:
    """Boundedly scan Edge benign sources into a temporary SQLite exact-row index for feasibility evidence."""
    seen = excluded = 0
    with TemporaryDirectory(prefix="datp_edge_index_") as temporary_directory:
        database = sqlite3.connect(Path(temporary_directory) / "edge.sqlite3")
        try:
            database.execute("PRAGMA journal_mode = OFF")
            database.execute(
                "CREATE TABLE canonical_rows (client_id TEXT, numeric_values TEXT, categorical_values TEXT, "
                "source_path TEXT, source_row_index INTEGER, "
                "PRIMARY KEY (client_id, numeric_values, categorical_values)) WITHOUT ROWID"
            )
            for path in sorted(source_paths):
                for result in iter_edge_iiotset_source(
                    path,
                    normal_root,
                    attack_root,
                    numeric_headers,
                    categorical_headers,
                    binary_label_header,
                    multiclass_label_header,
                ):
                    seen += 1
                    if isinstance(result, SourceRowFailure):
                        excluded += 1
                        continue
                    if result.is_attack or result.client_id is None:
                        continue
                    database.execute(
                        "INSERT OR IGNORE INTO canonical_rows VALUES (?, ?, ?, ?, ?)",
                        (
                            result.client_id,
                            struct.pack(f"!{len(result.numeric_values)}d", *result.numeric_values),
                            json.dumps(result.categorical_values, separators=(",", ":"), ensure_ascii=False),
                            result.source_path.as_posix(),
                            result.source_row_index,
                        ),
                    )
            canonical = int(database.execute("SELECT COUNT(*) FROM canonical_rows").fetchone()[0])
        finally:
            database.close()
    return EdgeIIoTsetExternalIndexReport(source_rows_seen=seen, excluded_rows=excluded, canonical_rows=canonical)


def split_edge_chronological_rows(
    rows: tuple[EdgeTimestampedRow, ...], materialization: DatasetMaterialization, excluded_clients: tuple[str, ...]
) -> EdgeChronologicalSplitRows:
    """Apply configured stable per-client chronology with cumulative midnight rollover correction."""
    if materialization.split_method != "within_client_chronological":
        raise ValueError("Edge-IIoTset chronological setup requires the configured within_client_chronological method")
    fractions = tuple(
        float(materialization.chronological_ratio(role))
        for role in ("historical_train", "historical_calibration", "future_recalibration", "future_evaluation")
    )
    if not math.isclose(sum(fractions), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("Edge-IIoTset chronological fractions must sum exactly to one")
    grouped: dict[str, list[EdgeTimestampedRow]] = {}
    for timestamped in rows:
        if timestamped.row.is_attack or timestamped.row.client_id is None:
            raise ValueError("Edge-IIoTset chronological split accepts assigned benign rows only")
        if not math.isfinite(timestamped.time_of_day_seconds) or not 0 <= timestamped.time_of_day_seconds < 86_400:
            raise ValueError("Edge-IIoTset time-of-day values must be finite seconds within one day")
        grouped.setdefault(timestamped.row.client_id, []).append(timestamped)
    roles = ([], [], [], [])
    for client_id, client_rows in sorted(grouped.items()):
        if client_id in excluded_clients:
            continue
        corrected: list[tuple[float, EdgeIIoTsetRow]] = []
        offset = 0.0
        previous: float | None = None
        for item in sorted(client_rows, key=lambda value: _provenance_key(value.row)):
            if previous is not None and item.time_of_day_seconds < previous:
                offset += 86_400
            corrected.append((item.time_of_day_seconds + offset, item.row))
            previous = item.time_of_day_seconds
        ordered = [row for _, row in sorted(corrected, key=lambda value: (value[0], _provenance_key(value[1])))]
        boundaries = [int(sum(fractions[: index + 1]) * len(ordered)) for index in range(3)]
        for index, row in enumerate(ordered):
            roles[_split_role(index, boundaries)].append(row)
    return EdgeChronologicalSplitRows(
        historical_train=tuple(roles[0]),
        historical_calibration=tuple(roles[1]),
        future_recalibration=tuple(roles[2]),
        future_evaluation=tuple(roles[3]),
        excluded_clients=tuple(sorted(set(excluded_clients))),
    )


def _provenance_key(row: EdgeIIoTsetRow) -> tuple[str, int]:
    return (row.source_path.as_posix(), row.source_row_index)


def _time_of_day_seconds(value: str) -> float:
    """Parse the configured Edge year-and-time field without inventing an absolute date."""
    try:
        time_part = value.strip().split()[-1]
        hours, minutes, seconds = time_part.split(":")
        parsed = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    except (IndexError, ValueError) as exc:
        raise ValueError("invalid time-of-day") from exc
    if not math.isfinite(parsed) or not 0.0 <= parsed < 86_400.0:
        raise ValueError("time-of-day is out of range")
    return parsed


def _category_value(value: str | None, known: tuple[str, ...]) -> str:
    """Map a categorical value to one of {known, __MISSING__, __UNKNOWN__}. (S3358)"""
    if value is None:
        return "__MISSING__"
    if value in known:
        return value
    return "__UNKNOWN__"


def _split_role(index: int, boundaries: tuple[int, int, int]) -> int:
    """Map an index to a chronological split role. (S3358)"""
    if index < boundaries[0]:
        return 0
    if index < boundaries[1]:
        return 1
    if index < boundaries[2]:
        return 2
    return 3


def _edge_content_hash(row: EdgeIIoTsetRow) -> str:
    return hashlib.blake2b(repr((row.numeric_values, row.categorical_values)).encode(), digest_size=32).hexdigest()


@define(frozen=True, slots=True, kw_only=True)
class EdgeIIoTsetMaterializationPayload:
    staged_path: Path
    row_count: int
    preprocessing_evidence: bytes
    partition_evidence: bytes | None = None


class EdgeIIoTsetAdapter:
    """Materialize standard and temporal Edge populations without assigning attacks to clients."""

    @property
    def adapter_kind(self) -> AdapterKind:
        return AdapterKind.EDGE_IIOTSET

    def materialize(
        self,
        dataset: ResolvedDataset,
        setup: DatasetSetup,
        materialization: DatasetMaterialization,
        inventory: SourceInventory,
        staging_root: Path,
        partition_condition: SweepConditionRecord | None,
        partition_seed_contract: PartitionSeedContract | None,
    ) -> EdgeIIoTsetMaterializationPayload:
        if partition_condition is not None or partition_seed_contract is not None:
            raise ValueError("Edge-IIoTset does not support partition-condition materialization")
        numeric = dataset.field_schema.retained_numeric_features
        categorical = dataset.field_schema.categorical_encoding
        labels = dataset.field_schema.label_fields
        inspection = dataset.inspection_contract
        if (
            numeric is None
            or not isinstance(categorical, CategoricalEncodingRecord)
            or labels.multiclass_label is None
            or inspection.normal_traffic_root is None
            or inspection.attack_traffic_root is None
            or inspection.binary_label_header is None
        ):
            raise ValueError("Edge-IIoTset materialization requires its resolved feature, label, and source contracts")
        timestamp = dataset.field_schema.identity_scheme.timestamp_field
        timestamp_header = timestamp.get("column") if isinstance(timestamp, Mapping) else timestamp
        if not isinstance(timestamp_header, str):
            raise ValueError("Edge-IIoTset timestamp field must resolve to a column name")
        normal_root = (dataset.paths.raw_data_root / inspection.normal_traffic_root.value).resolve()
        attack_root = (dataset.paths.raw_data_root / inspection.attack_traffic_root.value).resolve()
        excluded = frozenset(materialization.split_excluded_client_folders or ())
        rows = _read_edge_rows(
            inventory,
            normal_root,
            attack_root,
            numeric.order,
            categorical.columns,
            inspection.binary_label_header,
            labels.multiclass_label.column,
            timestamp_header if materialization.split_method == "within_client_chronological" else None,
            excluded,
        )
        rows = tuple(row for row in rows if row.client_id not in excluded)
        payload_file = staging_root / "materialized.parquet"
        if materialization.split_method == "random_fractional":
            split = split_edge_benign_rows(rows, materialization)
            vocabulary = fit_edge_vocabulary(split.train, categorical.columns)
            normalization = fit_edge_train_normalization(split.train)
            payload = encode_edge_split_as_parquet(split, numeric.order, vocabulary, normalization)
            evidence = {"split_method": materialization.split_method, "excluded_clients": sorted(excluded)}
        elif materialization.split_method == "within_client_chronological":
            chronological = split_edge_chronological_rows(
                tuple(
                    EdgeTimestampedRow(row=row, time_of_day_seconds=_require_edge_timestamp(row))
                    for row in _deduplicated_edge_benign_rows(rows)
                ),
                materialization,
                (),
            )
            _validate_edge_chronological_minimums(chronological, materialization)
            vocabulary = fit_edge_vocabulary(chronological.historical_train, categorical.columns)
            normalization = fit_edge_train_normalization(chronological.historical_train)
            payload = encode_edge_chronological_split_as_parquet(
                chronological, numeric.order, vocabulary, normalization
            )
            evidence = {
                "split_method": materialization.split_method,
                "excluded_clients": sorted(excluded),
                "chronology_validation": "passed",
            }
        else:
            raise ValueError(f"Unsupported Edge-IIoTset split method '{materialization.split_method}'")
        payload_file.write_bytes(payload)
        return EdgeIIoTsetMaterializationPayload(
            staged_path=payload_file,
            row_count=len(rows),
            preprocessing_evidence=json.dumps(evidence, sort_keys=True, separators=(",", ":")).encode(),
        )


def _read_edge_rows(
    inventory: SourceInventory,
    normal_root: Path,
    attack_root: Path,
    numeric_headers: tuple[str, ...],
    categorical_headers: tuple[str, ...],
    binary_label_header: str,
    multiclass_label_header: str,
    timestamp_header: str | None,
    excluded_clients: frozenset[str],
) -> tuple[EdgeIIoTsetRow, ...]:
    rows: list[EdgeIIoTsetRow] = []
    failures: list[str] = []
    for entry in inventory.entries:
        try:
            client_id = entry.source_path.relative_to(normal_root).parts[0]
        except ValueError:
            client_id = None
        if client_id in excluded_clients:
            continue
        for result in iter_edge_iiotset_source(
            entry.source_path,
            normal_root,
            attack_root,
            numeric_headers,
            categorical_headers,
            binary_label_header,
            multiclass_label_header,
            timestamp_header,
        ):
            if isinstance(result, SourceRowFailure):
                failures.append(f"{result.source_path}:{result.source_row_index}: {result.reason}")
            else:
                rows.append(result)
    if not rows:
        raise ValueError("Edge-IIoTset materialization found no valid source rows")
    return tuple(rows)


def _require_edge_timestamp(row: EdgeIIoTsetRow) -> float:
    if row.time_of_day_seconds is None:
        raise ValueError(f"Temporal Edge-IIoTset row lacks a timestamp: {row.source_path}:{row.source_row_index}")
    return row.time_of_day_seconds


def _deduplicated_edge_benign_rows(rows: tuple[EdgeIIoTsetRow, ...]) -> tuple[EdgeIIoTsetRow, ...]:
    canonical: dict[tuple[str, tuple[float, ...], tuple[str | None, ...]], EdgeIIoTsetRow] = {}
    for row in sorted(rows, key=lambda value: (value.source_path.as_posix(), value.source_row_index)):
        if row.is_attack:
            continue
        if row.client_id is None:
            raise ValueError("Edge-IIoTset benign rows require a folder-defined client")
        canonical.setdefault((row.client_id, row.numeric_values, row.categorical_values), row)
    if not canonical:
        raise ValueError("Temporal Edge-IIoTset materialization found no benign rows")
    return tuple(canonical.values())


def _validate_edge_chronological_minimums(split: EdgeChronologicalSplitRows, materialization: DatasetMaterialization) -> None:
    minimums = materialization.split_minimum_row_counts or {}
    roles = {
        "historical_train": split.historical_train,
        "historical_calibration": split.historical_calibration,
        "future_recalibration": split.future_recalibration,
        "future_evaluation": split.future_evaluation,
    }
    for client_id in {row.client_id for rows in roles.values() for row in rows}:
        if client_id is None:
            raise ValueError("Chronological Edge-IIoTset split contains an unassigned client")
        for role, rows in roles.items():
            required = minimums.get(role, 1)
            if sum(row.client_id == client_id for row in rows) < required:
                raise ValueError(f"Temporal client '{client_id}' lacks the configured minimum for {role}")
