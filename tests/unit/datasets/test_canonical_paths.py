from pathlib import Path

import pytest

from datp_core.data.canonical_cache import CanonicalAssetLayout, canonical_asset_path
from datp_core.data.contracts import CanonicalAssetRole
from datp_core.data.materialization import (
    canonical_data_partition_assets,
    empty_asset,
    named_assets,
    partition_assets,
)


def test_canonical_asset_layouts_are_publication_root_relative() -> None:
    partitions = canonical_data_partition_assets(2)
    assert tuple(asset.relative_path for asset in partitions) == (
        Path("data/part-00000.parquet"),
        Path("data/part-00001.parquet"),
    )

    nested = partition_assets(1, Path("training"), CanonicalAssetRole.CANONICAL_DATA)
    assert nested[0].relative_path == Path("training/part-00000.parquet")

    named = named_assets(Path("clients"), CanonicalAssetRole.CANONICAL_DATA, ("client-a", "client-b"))
    assert tuple(asset.relative_path for asset in named) == (
        Path("clients/client-a.parquet"),
        Path("clients/client-b.parquet"),
    )
    assert empty_asset(Path("clients"), CanonicalAssetRole.CANONICAL_DATA).relative_path == Path(
        "clients/empty.parquet"
    )


def test_canonical_asset_path_composes_publication_root_once(tmp_path: Path) -> None:
    root = tmp_path / "canonical" / "nbaiot"
    assert canonical_asset_path(root, Path("clients/client-a.parquet")) == root / "clients/client-a.parquet"


def test_canonical_asset_layout_rejects_escape_paths(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="publication-root-relative"):
        CanonicalAssetLayout(tmp_path / "absolute.parquet", CanonicalAssetRole.CANONICAL_DATA)
    with pytest.raises(ValueError, match="publication-root-relative"):
        CanonicalAssetLayout(Path("../escape.parquet"), CanonicalAssetRole.CANONICAL_DATA)
