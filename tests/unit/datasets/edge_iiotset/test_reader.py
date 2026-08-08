from datp_core.data.edge_iiotset.reader import EdgeIIoTsetReader
from datp_core.data.edge_iiotset.schema import EDGE_RAW_COLUMNS


def test_edge_benign_reader_adds_sensor_identity(tmp_path) -> None:
    path = tmp_path / "Distance" / "Distance.csv"
    path.parent.mkdir()
    path.write_text(",".join(EDGE_RAW_COLUMNS) + "\n", encoding="utf-8")
    assert "benign_sensor_group" in EdgeIIoTsetReader().read_benign(path).collect_schema().names()
