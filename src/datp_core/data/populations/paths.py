from enum import StrEnum
from pathlib import Path

from datp_core.core.identifiers import GlobPattern


class PartitioningArtifactDirectory(StrEnum):
    CANONICAL_DATA = "data"


class PartitioningFilePattern(StrEnum):
    PARQUET = "*.parquet"


def canonical_data_directory(canonical_root: Path) -> Path:
    return canonical_root / PartitioningArtifactDirectory.CANONICAL_DATA


def canonical_data_glob(canonical_root: Path) -> GlobPattern:
    return GlobPattern(str(canonical_data_directory(canonical_root) / PartitioningFilePattern.PARQUET))


def canonical_branch_directory(canonical_root: Path, branch: StrEnum) -> Path:
    return canonical_data_directory(canonical_root) / branch.value
