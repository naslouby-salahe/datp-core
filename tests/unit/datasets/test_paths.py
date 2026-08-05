from pathlib import Path

from datp_core.datasets.paths import canonical_root_under, raw_dataset_directory, raw_dataset_root
from datp_core.domain.enums import DatasetId, RawDatasetDirectory


def test_dataset_paths_are_enum_backed_and_root_relative() -> None:
    data_root = Path("workspace/data")

    assert raw_dataset_directory(DatasetId.NBAIOT) is RawDatasetDirectory.NBAIOT
    assert raw_dataset_root(data_root, DatasetId.CICIOT2023) == (
        data_root / "raw" / RawDatasetDirectory.CICIOT2023.value
    )
    assert canonical_root_under(data_root, DatasetId.CICIOT2023) == data_root / "canonical" / "ciciot2023"
    assert raw_dataset_directory(DatasetId.EDGE_IIOTSET) is RawDatasetDirectory.EDGE_IIOTSET
