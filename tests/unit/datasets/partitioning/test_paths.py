from enum import StrEnum
from pathlib import Path

from datp_core.datasets.partitioning.paths import (
    PartitioningFilePattern,
    canonical_branch_directory,
    canonical_data_directory,
    canonical_data_glob,
)


class _AssetBranch(StrEnum):
    BENIGN = "benign"


def test_partitioning_paths_are_owned_by_the_dataset_publication_root() -> None:
    root = Path("data/canonical/nbaiot")
    assert canonical_data_directory(root) == root / "data"
    assert canonical_data_glob(root) == str(root / "data" / PartitioningFilePattern.PARQUET)
    assert canonical_branch_directory(root, _AssetBranch.BENIGN) == root / "data" / "benign"
