"""N-BaIoT materialized-table Parquet encoding tests."""

from pathlib import Path

import polars as pl
from attrs import evolve

from datp_core.app import build_application
from datp_core.core.identifiers import DatasetId, DatasetSetupId, MaterializationId
from datp_core.core.values import PositiveInt
from datp_core.data.adapters.nbaiot import (
    apply_nbaiot_dirichlet_partition,
    consolidate_nbaiot_parquet_sources,
    encode_nbaiot_split_as_parquet,
    materialize_nbaiot_source_row,
    partition_dirichlet_rows,
    split_nbaiot_chronological_gapped_rows,
    write_nbaiot_source_parquet,
)
from datp_core.data.sources import SourceRow
from datp_core.experiments.models import SweepConditionAllocation, SweepConditionRecord


def test_dirichlet_partition_preserves_roles_capacity_and_seed_determinism() -> None:
    rows = tuple(
        (split, domain, f"{split}_{domain}.csv", row_index)
        for split in ("train", "calibration", "test")
        for domain in ("device_a", "device_b")
        for row_index in range(4)
    )

    condition = SweepConditionRecord(
        name="alpha_0_5", allocation=SweepConditionAllocation.DIRICHLET, dirichlet_alpha=0.5
    )
    first = partition_dirichlet_rows(rows, condition=condition, client_count=3, seed=0, retry_attempt=0)
    second = partition_dirichlet_rows(rows, condition=condition, client_count=3, seed=0, retry_attempt=0)

    assert first == second
    assert len(first.assignments) == len(rows)
    assert len({(path, row_index) for path, _, row_index, _ in first.assignments}) == len(rows)
    assert {client_id for _, _, _, client_id in first.assignments} == {"synthetic_00", "synthetic_01", "synthetic_02"}


def test_dirichlet_materialization_preserves_rows_and_emits_a_reproducible_manifest(tmp_path: Path) -> None:
    app = build_application()
    dataset = app.config.datasets[DatasetId("nbaiot")]
    setup = dataset.setup(DatasetSetupId("dirichlet_partitioned"))
    construction = evolve(
        setup.client_construction,
        client_count=PositiveInt(3),
        minimum_row_counts={"train": 1, "calibration": 1, "test": 1},
        retry_policy={"max_retries": 1},
    )
    condition = SweepConditionRecord(
        name="iid_reference",
        allocation=SweepConditionAllocation.EQUAL_ACROSS_SOURCE_DOMAINS,
        dirichlet_alpha=None,
    )
    source = tmp_path / "source.parquet"
    rows = [
        (split, domain, f"/{domain}/{split}.csv", index)
        for split in ("train", "calibration", "test")
        for domain in ("device_a", "device_b")
        for index in range(6)
    ]
    pl.DataFrame(
        {
            "split": [split for split, _, _, _ in rows],
            "client_id": [domain for _, domain, _, _ in rows],
            "source_path": [path for _, _, path, _ in rows],
            "source_row_index": [index for _, _, _, index in rows],
            "is_attack": [False] * len(rows),
            "feature_1": [float(index) for _, _, _, index in rows],
        }
    ).write_parquet(source)

    first_target = tmp_path / "first.parquet"
    second_target = tmp_path / "second.parquet"
    first = apply_nbaiot_dirichlet_partition(
        source,
        first_target,
        setup=construction,
        condition=condition,
        seed_key="datp_core.partition",
        digest_bytes=8,
    )
    second = apply_nbaiot_dirichlet_partition(
        source,
        second_target,
        setup=construction,
        condition=condition,
        seed_key="datp_core.partition",
        digest_bytes=8,
    )

    assert first == second
    assert (
        pl.read_parquet(first_target)
        .select("source_path", "source_row_index")
        .equals(pl.read_parquet(source).select("source_path", "source_row_index"))
    )
    assert all(proportions == (0.5, 0.5) for _, proportions in first.proportions)
    assert all(dict(counts) == {"calibration": 4, "test": 4, "train": 4} for _, counts in first.row_counts)
    assert b'"feasibility_status":"feasible"' in first.encode()


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
