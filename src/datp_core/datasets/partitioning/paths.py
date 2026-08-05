"""Canonical population-construction path contracts."""

from enum import StrEnum
from pathlib import Path


class PartitioningArtifactDirectory(StrEnum):
    CANONICAL_DATA = "data"


class PartitioningFilePattern(StrEnum):
    PARQUET = "*.parquet"


def canonical_data_directory(canonical_root: Path) -> Path:
    """Return the canonical data directory beneath one dataset publication root."""
    return canonical_root / PartitioningArtifactDirectory.CANONICAL_DATA


def canonical_data_glob(canonical_root: Path) -> str:
    """Return the Parquet glob for one canonical dataset publication."""
    return str(canonical_data_directory(canonical_root) / PartitioningFilePattern.PARQUET)


def canonical_branch_directory(canonical_root: Path, branch: StrEnum) -> Path:
    """Return one typed canonical asset branch beneath a dataset publication root."""
    return canonical_data_directory(canonical_root) / branch.value
