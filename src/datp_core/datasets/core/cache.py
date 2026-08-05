"""Deterministic canonical-dataset cache coordinates."""

from pathlib import Path

from datp_core.domain.enums import DatasetId, ReusableDataCoordinateKind


def canonical_root_under(data_root: Path, dataset: DatasetId) -> Path:
    return data_root / ReusableDataCoordinateKind.CANONICAL / dataset.value
