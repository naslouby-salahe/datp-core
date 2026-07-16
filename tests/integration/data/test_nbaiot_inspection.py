from pathlib import Path

import pytest

from datp_core.application.ports.data import InspectDatasetSourceRequest
from datp_core.domain.artifacts.keys import StorageRootKind, StorageRootSpec, StorageVisibility
from datp_core.domain.artifacts.lineage import FeatureSchemaIdentity
from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.data.datasets import Dataset, DatasetSpec
from datp_core.domain.errors import DatasetError
from datp_core.domain.runtime.admissibility import ChunkRowCount, CsvBlockBytes
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.nbaiot_inspection import NBaIoTSourceInspector
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.roots import bind_storage_root

_FEATURE_COLUMNS = "feature_a,feature_b,feature_c"
_STREAMING_CHUNK_POLICY = StreamingChunkPolicy(
    csv_block_bytes=CsvBlockBytes(value=8 * 1024 * 1024), parquet_batch_rows=ChunkRowCount(value=50_000)
)


def _write_csv(path: Path, *, rows: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [_FEATURE_COLUMNS]
    lines.extend(f"{index}.0,{index * 2}.0,{index * 3}.0" for index in range(rows))
    path.write_text("\n".join(lines) + "\n")


def _write_synthetic_source(raw_root: Path) -> None:
    _write_csv(raw_root / "DeviceOne" / "benign_traffic.csv", rows=5)
    _write_csv(raw_root / "DeviceOne" / "gafgyt_attacks" / "combo.csv", rows=3)
    _write_csv(raw_root / "DeviceOne" / "mirai_attacks" / "syn.csv", rows=2)
    _write_csv(raw_root / "DeviceTwo" / "benign_traffic.csv", rows=4)
    _write_csv(raw_root / "DeviceTwo" / "gafgyt_attacks" / "udp.csv", rows=1)


def _inspector(raw_root: Path, artifact_root: Path) -> NBaIoTSourceInspector:
    store = FileArtifactStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.PROCESSED_DATA, visibility=StorageVisibility.SCIENTIFIC_OUTPUT),
            absolute_path=artifact_root,
        )
    )
    return NBaIoTSourceInspector(
        raw_root=raw_root, artifact_store=store, streaming_chunk_policy=_STREAMING_CHUNK_POLICY
    )


def _request(input_dim: int) -> InspectDatasetSourceRequest:
    return InspectDatasetSourceRequest(
        dataset=DatasetSpec(
            dataset=Dataset.N_BAIOT,
            input_dim=input_dim,
            feature_schema_identity=FeatureSchemaIdentity(value=StageFingerprint(value="a" * 64)),
            feature_count_verified=True,
        )
    )


def test_inspection_produces_a_stable_feature_order_and_manifest_artifacts(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_synthetic_source(raw_root)
    inspector = _inspector(raw_root, tmp_path / "manifests")

    result = inspector.inspect(_request(input_dim=3))

    assert result.timestamp_evidence is None
    assert result.source_manifest.artifact_id.value.startswith("artifact-")
    assert result.feature_schema_manifest.artifact_id.value.startswith("artifact-")


def test_inspection_is_deterministic_across_repeated_runs(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_synthetic_source(raw_root)
    inspector = _inspector(raw_root, tmp_path / "manifests")

    first = inspector.inspect(_request(input_dim=3))
    second = inspector.inspect(_request(input_dim=3))

    assert first.source_row_identity == second.source_row_identity
    assert first.source_manifest == second.source_manifest
    assert first.feature_schema_manifest == second.feature_schema_manifest


def test_inspection_rejects_a_configured_input_dimension_mismatch(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_synthetic_source(raw_root)
    inspector = _inspector(raw_root, tmp_path / "manifests")
    request = _request(input_dim=115)

    with pytest.raises(DatasetError):
        inspector.inspect(request)


def test_inspection_rejects_an_inconsistent_feature_schema_across_files(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_synthetic_source(raw_root)
    (raw_root / "DeviceTwo" / "gafgyt_attacks" / "udp.csv").write_text("feature_a,feature_b\n1.0,2.0\n")
    inspector = _inspector(raw_root, tmp_path / "manifests")
    request = _request(input_dim=3)

    with pytest.raises(DatasetError):
        inspector.inspect(request)


def test_inspection_rejects_an_empty_raw_root(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    raw_root.mkdir()
    inspector = _inspector(raw_root, tmp_path / "manifests")
    request = _request(input_dim=3)

    with pytest.raises(DatasetError):
        inspector.inspect(request)


def test_inspection_rejects_a_device_directory_with_no_matching_source_files(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    (raw_root / "DeviceEmpty").mkdir(parents=True)
    inspector = _inspector(raw_root, tmp_path / "manifests")
    request = _request(input_dim=3)

    with pytest.raises(DatasetError):
        inspector.inspect(request)


def test_inspection_rejects_a_header_only_source_file(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_synthetic_source(raw_root)
    (raw_root / "DeviceOne" / "benign_traffic.csv").write_text(_FEATURE_COLUMNS + "\n")
    inspector = _inspector(raw_root, tmp_path / "manifests")
    request = _request(input_dim=3)

    with pytest.raises(DatasetError):
        inspector.inspect(request)
