from datp_core.datasets.edge_iiotset.schema import EDGE_BENIGN_SENSOR_GROUPS, EDGE_RAW_COLUMNS


def test_audited_edge_schema() -> None:
    assert len(EDGE_RAW_COLUMNS) == 63
    assert len(EDGE_BENIGN_SENSOR_GROUPS) == 10
