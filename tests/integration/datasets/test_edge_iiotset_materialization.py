import struct
from datetime import UTC, datetime

import pyarrow.parquet as pq

from datp_core.datasets.edge_iiotset.materialize import EdgeIIoTsetMaterializer
from datp_core.datasets.edge_iiotset.schema import EDGE_ARROW_SCHEMA, EDGE_RAW_COLUMNS, EdgeAssetRole


def _write_edge(path, timestamp: str, label: str, attack_type: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        ",".join(EDGE_RAW_COLUMNS) + "\n" + ",".join((timestamp,) + ("0",) * 60 + (label, attack_type)),
        encoding="utf-8",
    )


def _write_pcap(path) -> None:
    capture = datetime(2021, 12, 27, 22, 58, 21, 314757, tzinfo=UTC)
    with path.open("wb") as destination:
        destination.write(struct.pack("<IHHIIII", 0xA1B2C3D4, 2, 4, 0, 0, 262_144, 1))
        destination.write(struct.pack("<IIII", int(capture.timestamp()), capture.microsecond, 0, 0))


def test_edge_materialization_separates_static_temporal_and_unassigned_attack(tmp_path) -> None:
    benign = tmp_path / "Distance" / "Distance.csv"
    attack = tmp_path / "Attack traffic" / "Backdoor_attack.csv"
    _write_edge(benign, "2021 23:58:21.314757000", "Normal", "")
    _write_pcap(benign.with_suffix(".pcap"))
    _write_edge(attack, "2021 23:58:22.314757000", "Attack", "Backdoor")

    published = EdgeIIoTsetMaterializer().materialize((benign,), (attack,), tmp_path / "canonical")

    assert published.canonical_root == tmp_path / "canonical" / "edge_iiotset"
    assert (published.canonical_root / "COMPLETE").is_file()
    assert len(published.assets) == 3
    assert published.row_count.value == 2
    assert all(pq.ParquetFile(asset.path).schema_arrow.equals(EDGE_ARROW_SCHEMA) for asset in published.assets)
    assert tuple(asset.role for asset in published.assets) == (
        EdgeAssetRole.STATIC_BENIGN,
        EdgeAssetRole.TEMPORAL_BENIGN,
        EdgeAssetRole.UNASSIGNED_ATTACK,
    )
    assert tuple(asset.source_identity for asset in published.assets) == ("Distance", "Distance", "Backdoor_attack")
    static_asset = next(asset for asset in published.assets if asset.role is EdgeAssetRole.STATIC_BENIGN)
    assert pq.read_table(static_asset.path, columns=["capture_timestamp"]).column(0).to_pylist()[0] is not None


def test_edge_keeps_invalid_chronology_static_and_excludes_it_from_temporal(tmp_path) -> None:
    modbus = tmp_path / "Modbus" / "Modbus.csv"
    attack = tmp_path / "Attack traffic" / "Backdoor_attack.csv"
    _write_edge(modbus, "192.168.0.128", "Normal", "")
    _write_edge(attack, "2021 23:58:22.314757000", "Attack", "Backdoor")

    published = EdgeIIoTsetMaterializer().materialize((modbus,), (attack,), tmp_path / "canonical")

    assert published.validation_report is not None
    assert published.validation_report.excluded_rows.value == 0
    assert len(published.validation_report.issues) == 1
    assert any(asset.path.name == "empty.parquet" for asset in published.assets)
    assert any(asset.role is EdgeAssetRole.STATIC_BENIGN for asset in published.assets)
