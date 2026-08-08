from datp_core.data.ciciot2023.schema import CICIOT2023_FEATURE_COLUMNS, CICIOT2023_LABELS


def test_audited_ciciot_schema() -> None:
    assert len(CICIOT2023_FEATURE_COLUMNS) == 39
    assert "BENIGN" in CICIOT2023_LABELS
