from pathlib import Path

from datp_core.core.identifiers import DatasetId, PreparedDataCoordinateKind, RawDatasetDirectory


def raw_dataset_directory(dataset: DatasetId) -> RawDatasetDirectory:
    return RawDatasetDirectory[dataset.name]


def raw_dataset_root(data_root: Path, dataset: DatasetId) -> Path:

    return data_root / PreparedDataCoordinateKind.RAW / raw_dataset_directory(dataset).value


def canonical_root_under(data_root: Path, dataset: DatasetId) -> Path:

    return data_root / PreparedDataCoordinateKind.CANONICAL / dataset.value
