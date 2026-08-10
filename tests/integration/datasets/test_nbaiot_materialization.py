from pathlib import Path

import polars as pl
import pyarrow.parquet as pq

from datp_core.core.identifiers import DatasetId
from datp_core.data.contracts import ExclusionReason
from datp_core.data.nbaiot.materialize import NBaIoTMaterializer
from datp_core.data.nbaiot.schema import NBAIOT_ARROW_SCHEMA, NBAIOT_FEATURE_COLUMNS, NBaIoTArtifactName


def _write_source(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        ",".join(NBAIOT_FEATURE_COLUMNS) + "\n" + ",".join(value for _ in NBAIOT_FEATURE_COLUMNS), encoding="utf-8"
    )


def test_nbaio_materialization_streams_complete_partitions(tmp_path, monkeypatch) -> None:
    benign = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    attack = tmp_path / "Danmini_Doorbell" / "gafgyt_attacks" / "ack.csv"
    _write_source(benign, "1")
    _write_source(attack, "2")

    def reject_arrow_conversion(_frame: pl.DataFrame) -> None:
        raise AssertionError("canonical materialization must not convert a whole frame to Arrow")

    monkeypatch.setattr(pl.DataFrame, "to_arrow", reject_arrow_conversion)
    materializer = NBaIoTMaterializer()
    published = materializer.materialize((attack, benign), tmp_path / "canonical")

    assert published.canonical_root == tmp_path / "canonical" / "nbaiot"
    assert (published.canonical_root / "dataset_manifest.json").is_file()
    assert (published.canonical_root / "schema.json").is_file()
    assert len(published.assets) == 2
    assert all(pq.ParquetFile(asset.path).schema_arrow.equals(NBAIOT_ARROW_SCHEMA) for asset in published.assets)
    assert all(
        "/tmp/" not in pl.read_parquet(asset.path, columns=["source_path"]).item(0, 0) for asset in published.assets
    )


def test_nbaiot_publish_records_excluded_raw_file_with_provenance(tmp_path: Path) -> None:
    benign = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    _write_source(benign, "1")
    demonstration = tmp_path / "Danmini_Doorbell" / NBaIoTArtifactName.STRUCTURE_DEMONSTRATION_FILE
    _write_source(demonstration, "1")

    published = NBaIoTMaterializer().publish(tmp_path, tmp_path / "canonical")

    assert published.inventory.excluded_source_count.value == 1
    excluded = published.inventory.excluded_sources[0]
    assert excluded.dataset is DatasetId.NBAIOT
    assert excluded.relative_path.name == NBaIoTArtifactName.STRUCTURE_DEMONSTRATION_FILE
    assert excluded.relative_path.parent.name == "Danmini_Doorbell"
    assert excluded.reason is ExclusionReason.UNRECOGNIZED_SOURCE
    assert published.inventory.accepted_source_count.value == 1
    assert '"excluded_sources"' in published.manifest_path.read_text(encoding="utf-8")
