from pathlib import Path

import pytest

from datp_core.application.ports.data import ClientPartitionRequest
from datp_core.domain.artifacts.keys import SerializationFormat, StorageRootKind, StorageRootSpec, StorageVisibility
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import DatasetSourceInspectionResult, Regime
from datp_core.domain.data.partitioning import ClientDefinitionStrategy, NaturalDevicePartitionSpec
from datp_core.domain.errors import PartitionError
from datp_core.domain.runtime.admissibility import ChunkRowCount, CsvBlockBytes
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.nbaiot.partitioning import NBaIoTNaturalDevicePartitioner
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


def _write_nine_devices(raw_root: Path) -> dict[str, int]:
    device_row_counts: dict[str, int] = {}
    for index in range(9):
        device_id = f"Device{index:02d}"
        rows = 5 + index
        _write_csv(raw_root / device_id / "benign_traffic.csv", rows=rows)
        _write_csv(raw_root / device_id / "gafgyt_attacks" / "combo.csv", rows=rows)
        device_row_counts[device_id] = rows * 2
    return device_row_counts


def _partitioner(raw_root: Path, tmp_path: Path) -> NBaIoTNaturalDevicePartitioner:
    store = FileArtifactStore(
        root=bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.PROCESSED_DATA, visibility=StorageVisibility.SCIENTIFIC_OUTPUT),
            absolute_path=tmp_path / "manifests",
        )
    )
    return NBaIoTNaturalDevicePartitioner(
        raw_root=raw_root,
        materialized_root=tmp_path / "materialized",
        artifact_store=store,
        streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
    )


def _dummy_ref() -> ArtifactRef:
    return ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "b" * 64),
        artifact_type=ArtifactType.SOURCE_INSPECTION,
        content_hash="b" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )


def _request() -> ClientPartitionRequest:
    return ClientPartitionRequest(
        inspection=DatasetSourceInspectionResult(
            source_manifest=_dummy_ref(),
            feature_schema_manifest=_dummy_ref(),
            source_row_identity=DatasetSourceIdentity(value=StageFingerprint(value="a" * 64)),
            timestamp_evidence=None,
        ),
        partitioning=NaturalDevicePartitionSpec(strategy=ClientDefinitionStrategy.NATURAL_DEVICE, regime=Regime.A),
    )


def test_partitioning_produces_exactly_nine_deterministic_clients_preserving_every_row(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    device_row_counts = _write_nine_devices(raw_root)
    partitioner = _partitioner(raw_root, tmp_path)
    request = _request()

    result = partitioner.partition(request)

    assert len(result.client_roster.client_ids) == 9
    assert tuple(client_id.value for client_id in result.client_roster.client_ids) == tuple(sorted(device_row_counts))
    assert result.client_roster.client_ids == tuple(sorted(result.client_roster.client_ids, key=lambda c: c.value))


def test_partitioning_is_deterministic_across_repeated_runs(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    _write_nine_devices(raw_root)
    request = _request()

    first = _partitioner(raw_root, tmp_path / "first").partition(request)
    second = _partitioner(raw_root, tmp_path / "second").partition(request)

    assert first.partition_identity == second.partition_identity
    assert first.client_roster == second.client_roster


def test_partitioning_rejects_a_device_count_other_than_nine(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    for index in range(5):
        _write_csv(raw_root / f"Device{index}" / "benign_traffic.csv", rows=3)
    partitioner = _partitioner(raw_root, tmp_path)
    request = _request()

    with pytest.raises(PartitionError):
        partitioner.partition(request)
