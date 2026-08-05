from pathlib import Path

from datp_core.datasets.core.contracts import raw_dataset_directory, raw_dataset_root
from datp_core.domain.enums import DatasetId, RawDatasetDirectory


def test_raw_dataset_directories_are_enum_backed() -> None:
    assert raw_dataset_directory(DatasetId.NBAIOT) is RawDatasetDirectory.NBAIOT
    assert raw_dataset_root(DatasetId.CICIOT2023) == Path(f"data/raw/{RawDatasetDirectory.CICIOT2023.value}")
    assert raw_dataset_directory(DatasetId.EDGE_IIOTSET) is RawDatasetDirectory.EDGE_IIOTSET
