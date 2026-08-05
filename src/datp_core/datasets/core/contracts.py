"""Typed canonical and raw dataset path contracts."""

from pathlib import Path

from datp_core.domain.enums import DatasetId, RawDatasetDirectory, ReusableDataCoordinateKind
from datp_core.protocols.runtime import DATA_ROOT


def raw_dataset_directory(dataset: DatasetId) -> RawDatasetDirectory:
    return RawDatasetDirectory[dataset.name]


def raw_dataset_root(dataset: DatasetId) -> Path:
    return DATA_ROOT / ReusableDataCoordinateKind.RAW / raw_dataset_directory(dataset).value


def canonical_root_under(data_root: Path, dataset: DatasetId) -> Path:
    return data_root / ReusableDataCoordinateKind.CANONICAL / dataset.value
