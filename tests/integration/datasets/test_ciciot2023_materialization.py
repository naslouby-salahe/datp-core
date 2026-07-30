from hashlib import sha256

import pyarrow.parquet as pq

from datp_core.datasets.ciciot2023.materialize import CICIoT2023Materializer
from datp_core.datasets.ciciot2023.schema import (
    CICIOT2023_ARROW_SCHEMA,
    CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS,
    CICIOT2023_RAW_COLUMNS,
)
from datp_core.domain.enums import AvailabilityStatus, PublicationStatus
from datp_core.domain.values import RowCount


def _write_merged(path, rate: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        ",".join(CICIOT2023_RAW_COLUMNS) + "\n" + ",".join(("1",) * 3 + (rate,) + ("1",) * 35 + (label,)),
        encoding="utf-8",
    )


def test_ciciot_materialization_uses_complete_reusable_schema_partitions(tmp_path) -> None:
    source = tmp_path / "MERGED_CSV" / "Merged01.csv"
    _write_merged(source, "1", "BENIGN")
    materializer = CICIoT2023Materializer()
    published = materializer.materialize((source,), tmp_path / "canonical")
    reused = materializer.materialize((source,), tmp_path / "canonical")

    assert published.canonical_root == tmp_path / "canonical" / "ciciot2023"
    assert (published.canonical_root / "COMPLETE").is_file()
    assert published.validation_report is not None
    assert published.validation_report.status is AvailabilityStatus.AVAILABLE
    assert pq.ParquetFile(published.assets[0].path).schema_arrow.equals(CICIOT2023_ARROW_SCHEMA)
    assert set(CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS).issubset(
        pq.ParquetFile(published.assets[0].path).schema_arrow.names
    )
    assert '"eligibility_policy"' in published.manifest_path.read_text(encoding="utf-8")
    assert reused.publication_status is PublicationStatus.REUSED


def test_ciciot_rate_anomalies_are_preserved_with_an_unavailable_report(tmp_path) -> None:
    source = tmp_path / "MERGED_CSV" / "Merged01.csv"
    _write_merged(source, "inf", "BENIGN")
    materializer = CICIoT2023Materializer()
    _, _, report = materializer.audit((source,))

    assert report.status is AvailabilityStatus.UNAVAILABLE
    assert report.invalid_rows == RowCount(1)
    published = materializer.materialize((source,), tmp_path / "canonical")
    assert published.validation_report is not None
    assert published.validation_report.status is AvailabilityStatus.UNAVAILABLE
    assert published.validation_report.invalid_rows == RowCount(1)


def test_ciciot_rebuilds_when_the_persisted_eligibility_policy_changes(tmp_path) -> None:
    source = tmp_path / "MERGED_CSV" / "Merged01.csv"
    _write_merged(source, "1", "BENIGN")
    materializer = CICIoT2023Materializer()
    published = materializer.materialize((source,), tmp_path / "canonical")
    manifest = published.manifest_path.read_text(encoding="utf-8")
    altered_manifest = manifest.replace('"eligibility_policy":{"checksum":"', '"eligibility_policy":{"checksum":"x', 1)
    assert altered_manifest != manifest
    published.manifest_path.write_text(altered_manifest, encoding="utf-8")
    schema = published.canonical_root / "schema.json"
    (published.canonical_root / "COMPLETE").write_text(
        sha256(f"{altered_manifest}\n{schema.read_text(encoding='utf-8')}".encode()).hexdigest(),
        encoding="utf-8",
    )

    rebuilt = materializer.materialize((source,), tmp_path / "canonical")

    assert rebuilt.publication_status is PublicationStatus.PUBLISHED
