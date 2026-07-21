"""Normalization fits only benign training rows and preserves the payload schema."""

from pathlib import Path

import polars as pl

from datp_core.infrastructure.tables.parquet_io import normalize_materialized_parquet


def test_global_train_min_max_normalization_does_not_fit_on_held_out_rows(tmp_path: Path) -> None:
    source_path = tmp_path / "source.parquet"
    target_path = tmp_path / "normalized.parquet"
    pl.DataFrame(
        {
            "split": ["train", "train", "test"],
            "client_id": ["c1", "c2", "c1"],
            "is_attack": [False, False, True],
            "feature": [2.0, 4.0, 10.0],
        }
    ).write_parquet(source_path)

    evidence = normalize_materialized_parquet(
        source_path, target_path, feature_columns=("feature",), strategy="min_max", scope="global_train"
    )

    normalized = pl.read_parquet(target_path)
    assert normalized["feature"].to_list() == [0.0, 1.0, 4.0]
    assert normalized.columns == ["split", "client_id", "is_attack", "feature"]
    assert b'"location":2.0' in evidence.encode()


def test_per_client_train_standardization_uses_population_standard_deviation(tmp_path: Path) -> None:
    source_path = tmp_path / "source.parquet"
    target_path = tmp_path / "normalized.parquet"
    pl.DataFrame(
        {
            "split": ["train", "train", "test"],
            "client_id": ["c1", "c1", "c1"],
            "is_attack": [False, False, False],
            "feature": [2.0, 4.0, 5.0],
        }
    ).write_parquet(source_path)

    normalize_materialized_parquet(
        source_path, target_path, feature_columns=("feature",), strategy="standard", scope="per_client_train"
    )

    normalized = pl.read_parquet(target_path)
    assert normalized["feature"].to_list() == [-1.0, 1.0, 2.0]
