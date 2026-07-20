"""Dataset audit tests for CICIoT2023."""

from pathlib import Path

from datp_core.composition.root import build_application
from datp_core.domain.identifiers import DatasetId


def test_ciciot2023_dataset_audit(tmp_path: Path) -> None:
    app = build_application()
    report = app.audit_dataset.execute(DatasetId("ciciot2023"), raw_root=tmp_path)
    assert report.dataset_id.value == "ciciot2023"
    assert report.readable is False
