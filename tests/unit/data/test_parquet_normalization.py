"""Normalization fits only benign training rows and preserves the payload schema."""

from __future__ import annotations

from pathlib import Path

import duckdb
import msgspec
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datp_core.data.contracts.enums import (
    ConstantFeaturePolicy,
    HashAlgorithm,
    MaterializedColumn,
    NormalizationFitScope,
    NormalizationStrategy,
    OutOfRangePolicy,
    ParquetCompression,
)
from datp_core.data.contracts.materialization import (
    DataLoadingConfig,
    DuckDbRuntimeConfig,
    HashConfig,
    MinMaxNormalizationConfig,
    ParquetWriteConfig,
    StandardNormalizationConfig,
)
from datp_core.data.materialization.errors import DataFailure
from datp_core.data.materialization.normalization import (
    NormalizationEvidence,
    encode_normalization_evidence,
    normalize_materialized_parquet,
)


def _build_materialized_parquet(
    path: Path,
    splits: list[str],
    client_ids: list[str],
    is_attack: list[bool],
    **features: list[float],
) -> None:
    """Build a minimal materialized Parquet file for normalization tests."""
    arrays: dict[str, list] = {
        MaterializedColumn.SPLIT.value: splits,
        MaterializedColumn.CLIENT_ID.value: client_ids,
        MaterializedColumn.IS_ATTACK.value: is_attack,
    }
    arrays.update(features)
    pq.write_table(pa.table(arrays), path)


@pytest.fixture
def runtime() -> DataLoadingConfig:
    return DataLoadingConfig(
        chunk_row_count=1000,
        parquet=ParquetWriteConfig(
            compression=ParquetCompression.NONE,
            dictionary_encoding=False,
            row_group_size=1000,
            data_page_size=65536,
        ),
        duckdb=DuckDbRuntimeConfig(
            threads=1,
            memory_limit="128MB",
            preserve_insertion_order=False,
        ),
        row_digest=HashConfig(
            algorithm=HashAlgorithm.BLAKE2B,
            digest_bytes=16,
        ),
    )


def test_standard_global_train_uses_benign_train_only(tmp_path: Path, runtime: DataLoadingConfig) -> None:
    """Standard normalization with GLOBAL_TRAIN fits only benign train rows."""
    source = tmp_path / "source.parquet"
    target = tmp_path / "normalized.parquet"
    _build_materialized_parquet(
        source,
        splits=["train", "train", "test"],
        client_ids=["c1", "c2", "c1"],
        is_attack=[False, False, True],
        feature=[2.0, 4.0, 10.0],
    )

    connection = duckdb.connect(":memory:")
    config = StandardNormalizationConfig(
        strategy=NormalizationStrategy.STANDARD,
        fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
        standard_deviation_ddof=0,
        constant_feature_policy=ConstantFeaturePolicy.ZERO,
        out_of_range_policy=OutOfRangePolicy.PRESERVE,
    )
    evidence = normalize_materialized_parquet(connection, source, target, ("feature",), config, runtime)

    normalized = pq.read_table(target)
    assert normalized.column("feature").to_pylist() == [-1.0, 1.0, 7.0]
    assert normalized.column_names == ["split", "client_id", "is_attack", "feature"]


def test_min_max_per_client_fits_per_client(tmp_path: Path, runtime: DataLoadingConfig) -> None:
    """Min-max normalization with PER_CLIENT_TRAIN fits per-client benign train rows."""
    source = tmp_path / "source.parquet"
    target = tmp_path / "normalized.parquet"
    _build_materialized_parquet(
        source,
        splits=["train", "train", "train", "train", "test"],
        client_ids=["c1", "c1", "c2", "c2", "c1"],
        is_attack=[False, False, False, False, False],
        feature=[2.0, 4.0, 10.0, 20.0, 3.0],
    )

    connection = duckdb.connect(":memory:")
    config = MinMaxNormalizationConfig(
        strategy=NormalizationStrategy.MIN_MAX,
        fit_scope=NormalizationFitScope.PER_CLIENT_TRAIN,
        constant_feature_policy=ConstantFeaturePolicy.ZERO,
        out_of_range_policy=OutOfRangePolicy.CLIP,
    )
    evidence = normalize_materialized_parquet(connection, source, target, ("feature",), config, runtime)

    normalized = pq.read_table(target)
    values = normalized.column("feature").to_pylist()
    # c1 train: [2.0, 4.0] => min=2.0, max=4.0 => 0.0, 1.0
    # c2 train: [10.0, 20.0] => min=10.0, max=20.0 => 0.0, 1.0
    # c1 test: (3.0 - 2.0) / (4.0 - 2.0) = 0.5
    assert values == [0.0, 1.0, 0.0, 1.0, pytest.approx(0.5)]


def test_calibration_rows_excluded_from_fit(tmp_path: Path, runtime: DataLoadingConfig) -> None:
    """Calibration-split rows do not affect normalization fit statistics."""
    source = tmp_path / "source.parquet"
    target = tmp_path / "normalized.parquet"
    _build_materialized_parquet(
        source,
        splits=["train", "train", "calibration"],
        client_ids=["c1", "c1", "c1"],
        is_attack=[False, False, False],
        feature=[2.0, 4.0, 100.0],
    )

    connection = duckdb.connect(":memory:")
    config = StandardNormalizationConfig(
        strategy=NormalizationStrategy.STANDARD,
        fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
        standard_deviation_ddof=0,
        constant_feature_policy=ConstantFeaturePolicy.ZERO,
        out_of_range_policy=OutOfRangePolicy.PRESERVE,
    )
    evidence = normalize_materialized_parquet(connection, source, target, ("feature",), config, runtime)

    normalized = pq.read_table(target)
    # fit: [2.0, 4.0] => mean=3.0, stddev_pop=1.0
    # train rows: (2-3)/1 = -1.0, (4-3)/1 = 1.0
    # calibration row: (100-3)/1 = 97.0
    assert normalized.column("feature").to_pylist() == [-1.0, 1.0, 97.0]


def test_attack_rows_excluded_from_fit(tmp_path: Path, runtime: DataLoadingConfig) -> None:
    """Attack rows in the training split do not affect normalization fit statistics."""
    source = tmp_path / "source.parquet"
    target = tmp_path / "normalized.parquet"
    _build_materialized_parquet(
        source,
        splits=["train", "train", "train"],
        client_ids=["c1", "c1", "c1"],
        is_attack=[False, False, True],
        feature=[2.0, 4.0, 100.0],
    )

    connection = duckdb.connect(":memory:")
    config = StandardNormalizationConfig(
        strategy=NormalizationStrategy.STANDARD,
        fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
        standard_deviation_ddof=0,
        constant_feature_policy=ConstantFeaturePolicy.ZERO,
        out_of_range_policy=OutOfRangePolicy.PRESERVE,
    )
    evidence = normalize_materialized_parquet(connection, source, target, ("feature",), config, runtime)

    normalized = pq.read_table(target)
    # benign train fit: [2.0, 4.0] => mean=3.0, stddev_pop=1.0
    # benign train rows: (2-3)/1 = -1.0, (4-3)/1 = 1.0
    # attack train row: (100-3)/1 = 97.0
    assert normalized.column("feature").to_pylist() == [-1.0, 1.0, 97.0]


def test_normalization_evidence_roundtrip(tmp_path: Path, runtime: DataLoadingConfig) -> None:
    """Evidence encodes and decodes with all fields preserved."""
    source = tmp_path / "source.parquet"
    target = tmp_path / "normalized.parquet"
    _build_materialized_parquet(
        source,
        splits=["train", "train"],
        client_ids=["c1", "c2"],
        is_attack=[False, False],
        feature=[2.0, 4.0],
    )

    connection = duckdb.connect(":memory:")
    config = StandardNormalizationConfig(
        strategy=NormalizationStrategy.STANDARD,
        fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
        standard_deviation_ddof=0,
        constant_feature_policy=ConstantFeaturePolicy.ZERO,
        out_of_range_policy=OutOfRangePolicy.PRESERVE,
    )
    evidence = normalize_materialized_parquet(connection, source, target, ("feature",), config, runtime)

    encoded = encode_normalization_evidence(evidence)
    decoded = msgspec.json.decode(encoded, type=NormalizationEvidence)

    assert decoded.schema_version == evidence.schema_version
    assert decoded.strategy == NormalizationStrategy.STANDARD.value
    assert decoded.fit_scope == NormalizationFitScope.GLOBAL_TRAIN.value
    assert decoded.feature_names == ("feature",)
    assert len(decoded.fitted_statistics) == 1
    assert decoded.fitted_statistics[0].client_id is None
    assert decoded.fitted_statistics[0].features[0].feature == "feature"
    assert decoded.fitted_statistics[0].features[0].location == 3.0
    assert decoded.fitted_statistics[0].features[0].scale == 1.0


def test_empty_feature_list_raises_error(tmp_path: Path, runtime: DataLoadingConfig) -> None:
    """An empty feature_names tuple raises DataFailure."""
    source = tmp_path / "source.parquet"
    target = tmp_path / "normalized.parquet"
    _build_materialized_parquet(
        source,
        splits=["train"],
        client_ids=["c1"],
        is_attack=[False],
        feature=[1.0],
    )

    connection = duckdb.connect(":memory:")
    config = MinMaxNormalizationConfig(
        strategy=NormalizationStrategy.MIN_MAX,
        fit_scope=NormalizationFitScope.GLOBAL_TRAIN,
        constant_feature_policy=ConstantFeaturePolicy.ZERO,
        out_of_range_policy=OutOfRangePolicy.CLIP,
    )

    with pytest.raises(DataFailure, match="normalization requires feature columns"):
        normalize_materialized_parquet(connection, source, target, (), config, runtime)
