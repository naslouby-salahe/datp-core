"""N-BaIoT materialized-table Parquet encoding tests."""

from pathlib import Path

import polars as pl

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import DatasetId, MaterializationId
from datp_core.infrastructure.datasets.csv_source import SourceRow
from datp_core.infrastructure.datasets.nbaiot import (
    consolidate_nbaiot_parquet_sources,
    encode_nbaiot_split_as_parquet,
    materialize_nbaiot_source_row,
    partition_dirichlet_rows,
    split_nbaiot_chronological_gapped_rows,
    write_nbaiot_source_parquet,
)


def test_dirichlet_partition_preserves_roles_capacity_and_seed_determinism() -> None:
    rows = tuple(
        (split, domain, f"{split}_{domain}.csv", row_index)
        for split in ("train", "calibration", "test")
        for domain in ("device_a", "device_b")
        for row_index in range(4)
    )

    first = partition_dirichlet_rows(rows, client_count=3, alpha=0.5, seed=0)
    second = partition_dirichlet_rows(rows, client_count=3, alpha=0.5, seed=0)

    assert first == second
    assert len(first.assignments) == len(rows)
    assert len({(path, row_index) for path, _, row_index, _ in first.assignments}) == len(rows)
    assert {client_id for _, _, _, client_id in first.assignments} == {"synthetic_00", "synthetic_01", "synthetic_02"}


def test_nbaiot_parquet_payload_carries_split_label_provenance_and_features(tmp_path: Path) -> None:
    root = tmp_path / "N-BaIoT"
    rows = tuple(
        materialize_nbaiot_source_row(
            SourceRow(
                source_path=root / "device" / "benign_traffic.csv", source_row_index=index, values=(float(index),)
            ),
            root,
            "benign_traffic.csv",
            ("gafgyt_attacks", "mirai_attacks"),
        )
        for index in range(1, 11)
    )
    split = split_nbaiot_chronological_gapped_rows(rows, 0.6, 0.0, 0.2, 0.0, 0.2)
    payload = encode_nbaiot_split_as_parquet(split, ("feature_1",))
    frame = pl.read_parquet(payload)
    assert frame.columns == [
        "split",
        "client_id",
        "is_attack",
        "attack_family",
        "source_path",
        "source_row_index",
        "feature_1",
    ]
    assert frame.height == 10
    assert set(frame["split"]) == {"train", "calibration", "test"}


def test_two_pass_nbaiot_writer_streams_configured_roles(tmp_path: Path) -> None:
    root = tmp_path / "N-BaIoT"
    source = root / "device" / "benign_traffic.csv"
    source.parent.mkdir(parents=True)
    source.write_text("feature_1\n" + "\n".join(str(value) for value in range(100)) + "\n")
    dataset = build_application().config.datasets[DatasetId("nbaiot")]
    materialization = next(item for item in dataset.materializations if item.identifier == MaterializationId("anchor"))
    output = tmp_path / "payload.parquet"
    assert (
        write_nbaiot_source_parquet(
            source,
            output,
            root,
            ("feature_1",),
            "benign_traffic.csv",
            ("gafgyt_attacks", "mirai_attacks"),
            materialization,
            7,
        )
        == 98
    )
    assert pl.read_parquet(output).group_by("split").len().sort("split").to_dict(as_series=False) == {
        "split": ["calibration", "test", "train"],
        "len": [20, 18, 60],
    }


def test_nbaiot_consolidation_streams_staged_parquet_files(tmp_path: Path) -> None:
    first = tmp_path / "first.parquet"
    second = tmp_path / "second.parquet"
    pl.DataFrame({"x": [1, 2]}).write_parquet(first)
    pl.DataFrame({"x": [3]}).write_parquet(second)
    output = tmp_path / "all.parquet"
    assert consolidate_nbaiot_parquet_sources((first, second), output, batch_size=1) == 3
    assert pl.read_parquet(output)["x"].to_list() == [1, 2, 3]
