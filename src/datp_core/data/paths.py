"""Typed canonical and raw dataset path contracts."""

from pathlib import Path

from datp_core.core.identifiers import DatasetId, PreparedDataCoordinateKind, RawDatasetDirectory


def raw_dataset_directory(dataset: DatasetId) -> RawDatasetDirectory:
    return RawDatasetDirectory[dataset.name]


def raw_dataset_root(data_root: Path, dataset: DatasetId) -> Path:
    """Resolve one dataset's raw root beneath the caller-owned data root."""
    return data_root / PreparedDataCoordinateKind.RAW / raw_dataset_directory(dataset).value


def canonical_root_under(data_root: Path, dataset: DatasetId) -> Path:
    """Resolve one dataset's canonical root beneath the caller-owned data root."""
    return data_root / PreparedDataCoordinateKind.CANONICAL / dataset.value
