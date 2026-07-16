from pathlib import Path
from tempfile import TemporaryDirectory

import msgspec
from hypothesis import given, settings
from hypothesis import strategies as st

from datp_core.application.ports.data import ClientPartitionRequest
from datp_core.domain.artifacts.keys import (
    ArtifactNamespace,
    DatasetArtifactKey,
    SerializationFormat,
    StorageRootKind,
    StorageRootSpec,
    StorageVisibility,
)
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import Dataset, DatasetSourceInspectionResult, Regime
from datp_core.domain.data.partitioning import (
    ClientDefinitionStrategy,
    ClientPartitionManifest,
    NaturalDevicePartitionSpec,
)
from datp_core.domain.runtime.admissibility import ChunkRowCount, CsvBlockBytes
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.partitioning import NaturalDevicePartitioner
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.paths import ArtifactPathResolver, ResolveArtifactLocationRequest
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


def _request() -> ClientPartitionRequest:
    dummy_ref = ArtifactRef(
        artifact_id=ArtifactId(value="artifact-" + "b" * 64),
        artifact_type=ArtifactType.SOURCE_INSPECTION,
        content_hash="b" * 64,
        schema_version=ArtifactSchemaVersion(value="v1"),
        serialization_format=SerializationFormat.JSON,
    )
    return ClientPartitionRequest(
        inspection=DatasetSourceInspectionResult(
            source_manifest=dummy_ref,
            feature_schema_manifest=dummy_ref,
            source_row_identity=DatasetSourceIdentity(value=StageFingerprint(value="a" * 64)),
            timestamp_evidence=None,
        ),
        partitioning=NaturalDevicePartitionSpec(strategy=ClientDefinitionStrategy.NATURAL_DEVICE, regime=Regime.A),
    )


@settings(deadline=1500)
@given(rows_per_device=st.lists(st.integers(min_value=1, max_value=20), min_size=9, max_size=9))
def test_every_source_row_is_mapped_to_exactly_one_client_with_no_loss_or_duplication(
    rows_per_device: list[int],
) -> None:
    with TemporaryDirectory() as raw_directory, TemporaryDirectory() as manifest_directory:
        raw_root = Path(raw_directory)
        total_written = 0
        for index, rows in enumerate(rows_per_device):
            _write_csv(raw_root / f"Device{index:02d}" / "benign_traffic.csv", rows=rows)
            total_written += rows
        bound_root = bind_storage_root(
            spec=StorageRootSpec(kind=StorageRootKind.PROCESSED_DATA, visibility=StorageVisibility.SCIENTIFIC_OUTPUT),
            absolute_path=Path(manifest_directory),
        )
        store = FileArtifactStore(root=bound_root)
        partitioner = NaturalDevicePartitioner(
            raw_root=raw_root,
            materialized_root=Path(manifest_directory) / "materialized",
            artifact_store=store,
            streaming_chunk_policy=_STREAMING_CHUNK_POLICY,
        )

        result = partitioner.partition(_request())

        assert len(result.client_roster.client_ids) == 9
        assert len(set(result.client_roster.client_ids)) == 9
        manifest_path = (
            ArtifactPathResolver()
            .resolve(
                ResolveArtifactLocationRequest(
                    key=DatasetArtifactKey(
                        artifact_type=ArtifactType.PARTITION_MANIFEST,
                        dataset=Dataset.N_BAIOT,
                        stage_identity=StageFingerprint(value=result.partition_manifest.content_hash),
                        namespace=ArtifactNamespace.DATP_ANCHOR,
                    ),
                    root=bound_root,
                    artifact=result.partition_manifest,
                )
            )
            .absolute_path
        )
        manifest = msgspec.json.decode(manifest_path.read_bytes(), type=ClientPartitionManifest)
        assert sum(membership.row_count for membership in manifest.client_row_memberships) == total_written
        assert len({membership.client_id for membership in manifest.client_row_memberships}) == 9
