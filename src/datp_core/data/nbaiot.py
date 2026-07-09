"""N-BaIoT raw discovery and typed CSV loading for the Regime A anchor."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import numpy as np


class NbaiotDataError(RuntimeError):
    """Raised when N-BaIoT input cannot satisfy the anchor dataset contract."""


class SampleSource(StrEnum):
    BENIGN = "benign"
    ATTACK = "attack"


SUPPORTED_EXTENSIONS = frozenset({".csv"})


@dataclass(frozen=True)
class RawFileRecord:
    path: str
    byte_count: int
    content_hash: str
    device_id: str | None
    source: SampleSource | None


@dataclass(frozen=True)
class DatasetInventory:
    root: str
    files: tuple[RawFileRecord, ...]
    unsupported_files: tuple[str, ...]
    missing_devices: tuple[str, ...]
    ambiguous_files: tuple[str, ...]

    @property
    def is_usable(self) -> bool:
        return any(record.device_id is not None and record.source is not None for record in self.files)


@dataclass(frozen=True)
class DeviceSamples:
    device_id: str
    source: SampleSource
    sample_ids: tuple[str, ...]
    features: np.ndarray

    def __post_init__(self) -> None:
        if not self.device_id:
            raise NbaiotDataError("device identity is required")
        if self.features.ndim != 2 or self.features.shape[0] != len(self.sample_ids):
            raise NbaiotDataError("sample IDs and feature rows must have matching two-dimensional shapes")
        self.features.setflags(write=False)


@dataclass
class _SampleAccumulator:
    device_id: str
    source: SampleSource
    feature_blocks: list[np.ndarray]
    sample_ids: list[str]


@dataclass(frozen=True)
class NbaiotDataset:
    feature_columns: tuple[str, ...]
    samples: tuple[DeviceSamples, ...]
    inventory: DatasetInventory

    def by_device(self, device_id: str, source: SampleSource) -> DeviceSamples:
        for samples in self.samples:
            if samples.device_id == device_id and samples.source is source:
                return samples
        raise NbaiotDataError(f"missing {source.value} samples for device {device_id!r}")

    @property
    def device_ids(self) -> tuple[str, ...]:
        return tuple(sorted({samples.device_id for samples in self.samples}))


def _infer_identity(path: Path, root: Path) -> tuple[str | None, SampleSource | None]:
    relative = path.relative_to(root)
    tokens = [part.lower() for part in relative.parts]
    source = next(
        (SampleSource.BENIGN for token in tokens if "benign" in token or "clean" in token),
        None,
    )
    if source is None:
        source = next(
            (SampleSource.ATTACK for token in tokens if "attack" in token or "malicious" in token),
            None,
        )
    device_id: str | None = relative.parts[0] if len(relative.parts) > 1 else None
    stem_parts = path.stem.split("__")
    if device_id is None and len(stem_parts) == 2:
        device_id = stem_parts[0]
    return device_id, source


def _content_hash_placeholder(path: Path) -> str:
    stat = path.stat()
    return f"metadata:{stat.st_size}:{stat.st_mtime_ns}"


def discover_nbaiot(root: Path) -> DatasetInventory:
    """Inventory raw CSV files without loading their tabular payloads into memory."""
    if not root.is_dir():
        raise NbaiotDataError(f"N-BaIoT raw directory is missing: {root}")
    paths = tuple(sorted(path for path in root.rglob("*") if path.is_file()))
    if not paths:
        raise NbaiotDataError(f"N-BaIoT raw directory is empty: {root}")
    records: list[RawFileRecord] = []
    unsupported: list[str] = []
    ambiguous: list[str] = []
    seen_benign_devices: set[str] = set()
    for path in paths:
        relative = str(path.relative_to(root))
        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            unsupported.append(relative)
            continue
        device_id, source = _infer_identity(path, root)
        if device_id is None or source is None:
            ambiguous.append(relative)
        elif source is SampleSource.BENIGN and device_id in seen_benign_devices:
            ambiguous.append(relative)
        elif source is SampleSource.BENIGN:
            seen_benign_devices.add(device_id)
        records.append(
            RawFileRecord(
                path=relative,
                byte_count=path.stat().st_size,
                content_hash=_content_hash_placeholder(path),
                device_id=device_id,
                source=source,
            )
        )
    return DatasetInventory(
        root=str(root),
        files=tuple(records),
        unsupported_files=tuple(unsupported),
        missing_devices=(),
        ambiguous_files=tuple(sorted(ambiguous)),
    )


def _read_csv_file(
    path: Path,
    device_id: str,
    known_columns: tuple[str, ...] | None,
) -> tuple[tuple[str, ...], np.ndarray, tuple[str, ...]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise NbaiotDataError(f"missing CSV header in {path}")
        columns = tuple(column for column in reader.fieldnames if column not in {"label", "source", "device_id"})
        if not columns:
            raise NbaiotDataError(f"missing feature columns in {path}")
        if known_columns is not None and columns != known_columns:
            raise NbaiotDataError(f"feature schema mismatch in {path}: {columns} != {known_columns}")
        rows = tuple(reader)
    if not rows:
        raise NbaiotDataError(f"no sample rows in {path}")
    if any("device_id" in row and row["device_id"] != device_id for row in rows):
        raise NbaiotDataError(f"mixed device identities in {path}")
    try:
        values = np.asarray([[float(row[column]) for column in columns] for row in rows], dtype=np.float64)
    except (KeyError, ValueError) as exc:
        raise NbaiotDataError(f"non-numeric or missing feature value in {path}") from exc
    return columns, values, tuple(f"{path.name}:{index}" for index in range(len(rows)))


def _accumulator_for(
    accumulators: list[_SampleAccumulator], device_id: str, source: SampleSource
) -> _SampleAccumulator:
    for accumulator in accumulators:
        if accumulator.device_id == device_id and accumulator.source is source:
            return accumulator
    accumulator = _SampleAccumulator(device_id, source, [], [])
    accumulators.append(accumulator)
    return accumulator


def load_nbaiot(root: Path) -> NbaiotDataset:
    """Load a discovered N-BaIoT CSV layout into immutable typed sample groups."""
    inventory = discover_nbaiot(root)
    fatal_ambiguities = tuple(path for path in inventory.ambiguous_files if "/" in path)
    if not inventory.is_usable or fatal_ambiguities:
        raise NbaiotDataError(
            f"N-BaIoT inventory is unusable: unsupported={inventory.unsupported_files}, ambiguous={fatal_ambiguities}"
        )
    accumulators: list[_SampleAccumulator] = []
    resolved_columns: tuple[str, ...] | None = None
    for record in inventory.files:
        if record.device_id is None or record.source is None:
            continue
        path = root / record.path
        columns, values, row_ids = _read_csv_file(path, record.device_id, resolved_columns)
        resolved_columns = columns
        accumulator = _accumulator_for(accumulators, record.device_id, record.source)
        accumulator.feature_blocks.append(values)
        accumulator.sample_ids.extend(f"{record.path}:{row_id}" for row_id in row_ids)
    if resolved_columns is None:
        raise NbaiotDataError("no N-BaIoT feature schema could be resolved")
    samples = tuple(
        DeviceSamples(
            device_id=accumulator.device_id,
            source=accumulator.source,
            sample_ids=tuple(accumulator.sample_ids),
            features=np.concatenate(accumulator.feature_blocks, axis=0),
        )
        for accumulator in sorted(accumulators, key=lambda item: (item.device_id, item.source.value))
    )
    return NbaiotDataset(feature_columns=resolved_columns, samples=samples, inventory=inventory)
