import pyarrow.parquet as pq

from datp_core.core.identifiers import AvailabilityStatus, DatasetId
from datp_core.core.numeric import RowCount
from datp_core.data.ciciot2023.materialize import CICIoT2023Materializer
from datp_core.data.ciciot2023.schema import (
    CICIOT2023_ARROW_SCHEMA,
    CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS,
    CICIOT2023_RAW_COLUMNS,
)
from datp_core.data.contracts import ExclusionReason


def _write_merged(path, rate: str, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        ",".join(CICIOT2023_RAW_COLUMNS) + "\n" + ",".join(("1",) * 3 + (rate,) + ("1",) * 35 + (label,)),
        encoding="utf-8",
    )


def test_ciciot_materialization_uses_schema_partitions(tmp_path) -> None:
    source = tmp_path / "MERGED_CSV" / "Merged01.csv"
    _write_merged(source, "1", "BENIGN")
    materializer = CICIoT2023Materializer()
    published = materializer.materialize((source,), tmp_path / "canonical")

    assert published.canonical_root == tmp_path / "canonical" / "ciciot2023"
    assert published.validation_report is not None
    assert published.validation_report.status is AvailabilityStatus.AVAILABLE
    assert pq.ParquetFile(published.assets[0].path).schema_arrow.equals(CICIOT2023_ARROW_SCHEMA)
    assert set(CICIOT2023_MODEL_INPUT_EVIDENCE_COLUMNS).issubset(
        pq.ParquetFile(published.assets[0].path).schema_arrow.names
    )
    assert '"eligibility_policy"' in published.manifest_path.read_text(encoding="utf-8")


def test_ciciot_rate_anomalies_are_preserved_with_an_unavailable_report(tmp_path) -> None:
    source = tmp_path / "MERGED_CSV" / "Merged01.csv"
    _write_merged(source, "inf", "BENIGN")
    materializer = CICIoT2023Materializer()
    report = materializer.audit((source,)).validation_report

    assert report.status is AvailabilityStatus.UNAVAILABLE
    assert report.invalid_rows == RowCount(1)
    published = materializer.materialize((source,), tmp_path / "canonical")
    assert published.validation_report is not None
    assert published.validation_report.status is AvailabilityStatus.UNAVAILABLE
    assert published.validation_report.invalid_rows == RowCount(1)


def test_ciciot_publish_records_excluded_non_merged_csv_with_provenance(tmp_path) -> None:
    source = tmp_path / "MERGED_CSV" / "Merged01.csv"
    _write_merged(source, "1", "BENIGN")
    stray = tmp_path / "documentation" / "readme.csv"
    _write_merged(stray, "1", "BENIGN")

    published = CICIoT2023Materializer().publish(tmp_path, tmp_path / "canonical")

    assert published.inventory.excluded_source_count.value == 1
    excluded = published.inventory.excluded_sources[0]
    assert excluded.dataset is DatasetId.CICIOT2023
    assert excluded.relative_path.name == "readme.csv"
    assert excluded.relative_path.parent.name == "documentation"
    assert excluded.reason is ExclusionReason.UNRECOGNIZED_SOURCE
    assert published.inventory.accepted_source_count.value == 1
    assert '"excluded_sources"' in published.manifest_path.read_text(encoding="utf-8")
