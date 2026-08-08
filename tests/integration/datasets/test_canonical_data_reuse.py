from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256

import pyarrow.parquet as pq

from datp_core.core.identifiers import PublicationStatus
from datp_core.data.nbaiot.materialize import NBaIoTMaterializer
from datp_core.data.nbaiot.schema import NBAIOT_FEATURE_COLUMNS


def _write_benign(path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        ",".join(NBAIOT_FEATURE_COLUMNS) + "\n" + ",".join(value for _ in NBAIOT_FEATURE_COLUMNS), encoding="utf-8"
    )


def test_corrupt_canonical_asset_is_deleted_and_rebuilt(tmp_path) -> None:
    source = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    _write_benign(source, "1")
    materializer = NBaIoTMaterializer()
    first = materializer.materialize((source,), tmp_path / "canonical")
    first.assets[0].path.write_bytes(b"not parquet")

    rebuilt = materializer.materialize((source,), tmp_path / "canonical")

    assert rebuilt.publication_status is PublicationStatus.PUBLISHED
    assert pq.ParquetFile(rebuilt.assets[0].path).metadata.num_rows == 1


def test_final_coordinate_lock_allows_one_publication_and_one_reuse(tmp_path) -> None:
    source = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    _write_benign(source, "1")

    def publish() -> PublicationStatus:
        return NBaIoTMaterializer().materialize((source,), tmp_path / "canonical").publication_status

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = tuple(executor.map(lambda _: publish(), range(2)))

    assert frozenset(statuses) == frozenset((PublicationStatus.PUBLISHED, PublicationStatus.REUSED))


def test_unchanged_source_reuses_manifest_bound_source_state(tmp_path) -> None:
    source = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    _write_benign(source, "1")
    materializer = NBaIoTMaterializer()
    published = materializer.materialize((source,), tmp_path / "canonical")

    reused = materializer.materialize((source,), tmp_path / "canonical")

    assert published.publication_status is PublicationStatus.PUBLISHED
    assert reused.publication_status is PublicationStatus.REUSED
    assert (reused.canonical_root / "source_state.json").is_file()


def test_changed_source_state_rebuilds_canonical_data(tmp_path) -> None:
    source = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    _write_benign(source, "1")
    materializer = NBaIoTMaterializer()
    materializer.materialize((source,), tmp_path / "canonical")
    _write_benign(source, "2")

    rebuilt = materializer.materialize((source,), tmp_path / "canonical")

    assert rebuilt.publication_status is PublicationStatus.PUBLISHED


def test_interrupted_temporary_publication_is_removed_before_rebuild(tmp_path) -> None:
    source = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    _write_benign(source, "1")
    materializer = NBaIoTMaterializer()
    target = materializer.canonical_directory(tmp_path / "canonical")
    interrupted = target.parent / f".{target.name}.interrupted"
    (interrupted / "data").mkdir(parents=True)

    materializer.materialize((source,), tmp_path / "canonical")

    assert interrupted.exists() is False


def test_rebuilds_when_persisted_validation_report_does_not_match_current_audit(tmp_path) -> None:
    source = tmp_path / "Danmini_Doorbell" / "benign_traffic.csv"
    _write_benign(source, "1")
    materializer = NBaIoTMaterializer()
    published = materializer.materialize((source,), tmp_path / "canonical")
    manifest_path = published.canonical_root / "dataset_manifest.json"
    schema_path = published.canonical_root / "schema.json"
    complete_path = published.canonical_root / "COMPLETE"
    manifest = manifest_path.read_text(encoding="utf-8")
    altered_manifest = manifest.replace('"accepted_rows":1', '"accepted_rows":2')
    assert altered_manifest != manifest
    manifest_path.write_text(altered_manifest, encoding="utf-8")
    complete_path.write_text(
        sha256(f"{altered_manifest}\n{schema_path.read_text(encoding='utf-8')}".encode()).hexdigest(),
        encoding="utf-8",
    )

    rebuilt = materializer.materialize((source,), tmp_path / "canonical")

    assert rebuilt.publication_status is PublicationStatus.PUBLISHED
