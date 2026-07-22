"""Calibration-window subsampling preserves the configured nested replicate contract."""

import polars as pl

from datp_core.infrastructure.tables.calibration_subsampling import subsample_calibration_scores


def _scores() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "client_id": ["a"] * 4 + ["b"] * 3,
            "source_path": ["a.csv"] * 4 + ["b.csv"] * 3,
            "source_row_index": [0, 1, 2, 3, 0, 1, 2],
            "score": [float(value) for value in range(7)],
        }
    )


def _sample(size: int, replicate: int = 0) -> pl.DataFrame:
    return subsample_calibration_scores(
        _scores(),
        requested_sample_count=size,
        training_seed=7,
        selection_seed=0,
        replicate=replicate,
        namespace_key="datp_core.calibration_subsample",
        digest_bytes=8,
    )


def test_calibration_subsamples_are_deterministic_nested_and_client_eligible() -> None:
    small = _sample(2)
    large = _sample(3)

    assert small.equals(_sample(2))
    assert set(small.filter(pl.col("client_id") == "a")["source_row_index"]) <= set(
        large.filter(pl.col("client_id") == "a")["source_row_index"]
    )
    assert set(small.filter(pl.col("client_id") == "b")["source_row_index"]) <= set(
        large.filter(pl.col("client_id") == "b")["source_row_index"]
    )
    assert _sample(4)["client_id"].unique().to_list() == ["a"]


def test_replicates_use_distinct_seeded_permutations() -> None:
    assert not _sample(2, replicate=0).equals(_sample(2, replicate=1))
