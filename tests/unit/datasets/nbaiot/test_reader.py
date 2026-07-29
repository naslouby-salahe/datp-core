import pytest

from datp_core.datasets.nbaiot.reader import NBaIoTReader
from datp_core.datasets.nbaiot.schema import NBAIOT_FEATURE_COLUMNS, NBaIoTDevice


def test_reader_is_lazy_for_audited_source(tmp_path) -> None:
    path = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    path.parent.mkdir()
    path.write_text(",".join(NBAIOT_FEATURE_COLUMNS) + "\n", encoding="utf-8")
    frame = NBaIoTReader().read(path)
    assert frame.collect_schema().names()[-1] == "stable_row_id"


def test_reader_preserves_relative_provenance_and_rejects_nonfinite_values(tmp_path) -> None:
    path = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    path.parent.mkdir()
    path.write_text(
        ",".join(NBAIOT_FEATURE_COLUMNS) + "\n" + ",".join("inf" for _ in NBAIOT_FEATURE_COLUMNS),
        encoding="utf-8",
    )
    reader = NBaIoTReader()
    frame = reader.read(path)

    assert frame.select("source_path").collect().item() == "Danmini_Doorbell/benign_traffic.csv"
    assert frame.select("physical_client_id").collect().item() == NBaIoTDevice.DANMINI_DOORBELL.value
    with pytest.raises(ValueError, match="non-finite"):
        reader.validate_finite_values(frame)
