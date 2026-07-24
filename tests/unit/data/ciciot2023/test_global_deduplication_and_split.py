"""CICIoT2023 global exact-deduplication and seeded split tests."""

from pathlib import Path

from datp_core.app import build_application
from datp_core.core.identifiers import DatasetId, MaterializationId
from datp_core.data.adapters.ciciot2023 import (
    CICIoT2023MaterializedRow,
    canonicalize_and_split_ciciot2023_rows,
    materialize_ciciot2023_merged_identity,
)
from datp_core.data.sources import SourceRow


def _row(root: Path, file_name: str, index: int, values: tuple[float, ...], label: str) -> CICIoT2023MaterializedRow:
    source_path = root / file_name
    return CICIoT2023MaterializedRow(
        identity=materialize_ciciot2023_merged_identity(source_path, index, root, label, "BENIGN"),
        multiclass_label=label,
        source_row=SourceRow(source_path=source_path, source_row_index=index, values=values),
    )


def test_global_exact_duplicates_are_canonicalized_before_seeded_split(tmp_path: Path) -> None:
    root = tmp_path / "MERGED_CSV"
    rows = (
        _row(root, "MergedB.csv", 2, (1.0, 2.0), "BENIGN"),
        _row(root, "MergedA.csv", 4, (1.0, 2.0), "BENIGN"),
        _row(root, "MergedA.csv", 5, (1.0, 2.0), "DDoS"),
        _row(root, "MergedA.csv", 1, (3.0, 4.0), "BENIGN"),
        _row(root, "MergedB.csv", 1, (5.0, 6.0), "Recon"),
    )
    dataset = build_application().config.datasets[DatasetId("ciciot2023")]
    materialization = next(
        item for item in dataset.materializations if item.identifier == MaterializationId("datp_core")
    )
    split = canonicalize_and_split_ciciot2023_rows(rows, materialization)
    all_rows = split.train + split.calibration + split.test
    assert len(all_rows) == 4
    assert split.deduplication.duplicate_rows_removed == 1
    assert split.deduplication.conflicting_label_feature_group_count == 1
    assert {(row.identity.source_path.name, row.identity.source_row_index) for row in all_rows} >= {
        ("MergedA.csv", 4),
        ("MergedA.csv", 5),
        ("MergedB.csv", 1),
    }
    assert all(not row.identity.is_attack for row in split.train + split.calibration)
    assert {
        (row.identity.source_path.name, row.identity.source_row_index) for row in split.test if row.identity.is_attack
    } == {
        ("MergedA.csv", 5),
        ("MergedB.csv", 1),
    }


def test_seeded_split_is_reproducible_and_a_class_cannot_cross_roles(tmp_path: Path) -> None:
    root = tmp_path / "MERGED_CSV"
    rows = tuple(_row(root, "Merged.csv", index, (float(index),), "BENIGN") for index in range(1, 31))
    dataset = build_application().config.datasets[DatasetId("ciciot2023")]
    materialization = next(
        item for item in dataset.materializations if item.identifier == MaterializationId("datp_core")
    )
    first = canonicalize_and_split_ciciot2023_rows(rows, materialization)
    second = canonicalize_and_split_ciciot2023_rows(rows, materialization)
    assert first == second
    assigned = first.train + first.calibration + first.test
    assert len({(row.source_row.values, row.identity.is_attack) for row in assigned}) == len(assigned)
