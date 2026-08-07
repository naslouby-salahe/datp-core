from pathlib import Path

import polars as pl
import pyarrow.parquet as pq

from datp_core.datasets.contracts import ExclusionReason
from datp_core.datasets.nbaiot.materialize import NBaIoTMaterializer
from datp_core.datasets.nbaiot.schema import NBAIOT_ARROW_SCHEMA, NBAIOT_FEATURE_COLUMNS, NBaIoTArtifactName
from datp_core.domain.enums import DatasetId, PublicationStatus


def _write_source(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        ",".join(NBAIOT_FEATURE_COLUMNS) + "\n" + ",".join(value for _ in NBAIOT_FEATURE_COLUMNS), encoding="utf-8"
    )


def test_nbaio_materialization_streams_complete_reusable_partitions(tmp_path, monkeypatch) -> None:
    benign = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    attack = tmp_path / "Danmini_Doorbell" / "gafgyt_attacks" / "ack.csv"
    _write_source(benign, "1")
    _write_source(attack, "2")

    def reject_arrow_conversion(_frame: pl.DataFrame) -> None:
        raise AssertionError("canonical materialization must not convert a whole frame to Arrow")

    monkeypatch.setattr(pl.DataFrame, "to_arrow", reject_arrow_conversion)
    materializer = NBaIoTMaterializer()
    published = materializer.materialize((attack, benign), tmp_path / "canonical")
    reused = materializer.materialize((benign, attack), tmp_path / "canonical")

    assert published.canonical_root == tmp_path / "canonical" / "nbaiot"
    assert (published.canonical_root / "COMPLETE").is_file()
    assert (published.canonical_root / "dataset_manifest.json").is_file()
    assert (published.canonical_root / "schema.json").is_file()
    assert len(published.assets) == 2
    assert reused.publication_status is PublicationStatus.REUSED
    assert all(pq.ParquetFile(asset.path).schema_arrow.equals(NBAIOT_ARROW_SCHEMA) for asset in published.assets)
    assert all(
        "/tmp/" not in pq.read_table(asset.path, columns=["source_path"]).column(0).to_pylist()[0]
        for asset in published.assets
    )


def test_nbaio_rebuilds_incomplete_and_source_changed_publications(tmp_path) -> None:
    source = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    _write_source(source, "1")
    materializer = NBaIoTMaterializer()
    first = materializer.materialize((source,), tmp_path / "canonical")
    first_checksum = first.source_inventory_checksum
    (first.canonical_root / "COMPLETE").unlink()

    rebuilt = materializer.materialize((source,), tmp_path / "canonical")
    assert rebuilt.publication_status is PublicationStatus.PUBLISHED
    assert (rebuilt.canonical_root / "COMPLETE").is_file()

    _write_source(source, "3")
    changed = materializer.materialize((source,), tmp_path / "canonical")
    assert changed.publication_status is PublicationStatus.PUBLISHED
    assert changed.source_inventory_checksum != first_checksum


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
