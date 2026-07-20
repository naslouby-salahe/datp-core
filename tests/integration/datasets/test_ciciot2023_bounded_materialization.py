"""Bounded CICIoT2023 merged CSV materialization integration test."""

from pathlib import Path

import polars as pl

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import DatasetId, MaterializationId
from datp_core.infrastructure.datasets.ciciot2023 import write_ciciot2023_materialized_parquet


def test_ciciot2023_merged_rows_are_globally_deduplicated_then_streamed_to_parquet(tmp_path: Path) -> None:
    merged_root = tmp_path / "MERGED_CSV"
    merged_root.mkdir()
    (merged_root / "MergedA.csv").write_text("feature,Label\n1,BENIGN\n2,DDoS\ninvalid,BENIGN\n")
    (merged_root / "MergedB.csv").write_text("feature,Label\n1,BENIGN\n1,DDoS\n3,BENIGN\n")
    dataset = build_application().config.datasets[DatasetId("ciciot2023")]
    materialization = next(
        item for item in dataset.materializations if item.identifier == MaterializationId("datp_core")
    )
    target = tmp_path / "materialized.parquet"
    report = write_ciciot2023_materialized_parquet(
        tuple(sorted(merged_root.glob("*.csv"))),
        target,
        ("feature",),
        "Label",
        merged_root,
        "BENIGN",
        materialization,
        2,
    )
    frame = pl.read_parquet(target)
    assert report.source_rows_seen == 6
    assert report.excluded_rows == 1
    assert report.canonical_rows == report.written_rows == 4
    assert report.duplicate_rows_removed == 1
    assert report.conflicting_label_feature_group_count == 1
    assert frame.filter(pl.col("is_attack")).select("split").unique().item() == "test"
    assert (
        frame.filter((pl.col("feature") == 1.0) & ~pl.col("is_attack"))
        .select("source_path")
        .item()
        .endswith("MergedA.csv")
    )
