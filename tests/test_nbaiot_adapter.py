"""Dataset audit tests for N-BaIoT."""

from pathlib import Path

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import DatasetId


def test_nbaiot_dataset_audit(tmp_path: Path) -> None:
    app = build_application()
    report = app.audit_dataset.execute(DatasetId("nbaiot"), raw_root=tmp_path)
    assert report.dataset_id.value == "nbaiot"
    assert report.readable is False
