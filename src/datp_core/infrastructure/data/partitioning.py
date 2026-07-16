from dataclasses import dataclass
from pathlib import Path

import msgspec

from datp_core.application.ports.data import ClientPartitionRequest
from datp_core.application.ports.persistence import WriteArtifactRequest
from datp_core.domain.artifacts.keys import ArtifactNamespace, DatasetArtifactKey, SerializationFormat, WriteDisposition
from datp_core.domain.artifacts.lineage import DatasetSourceIdentity, PartitionIdentity
from datp_core.domain.artifacts.manifests import ArtifactType
from datp_core.domain.artifacts.references import ArtifactId, ArtifactRef, ArtifactSchemaVersion, StageFingerprint
from datp_core.domain.data.datasets import Dataset
from datp_core.domain.data.partitioning import (
    ClientPartitionManifest,
    ClientPartitionResult,
    ClientRowMembership,
    NaturalDevicePartitionSpec,
)
from datp_core.domain.errors import PartitionError
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientRoster
from datp_core.domain.runtime.policies import StreamingChunkPolicy
from datp_core.infrastructure.data.nbaiot_inspection import sorted_device_directories
from datp_core.infrastructure.data.nbaiot_source import NBaIoTChunkedSourceAdapter
from datp_core.infrastructure.data.streaming import ParquetBatchStream
from datp_core.infrastructure.persistence.artifacts import FileArtifactStore
from datp_core.infrastructure.persistence.hashing import blake3_bytes_content_hash

_REGIME_A_DEVICE_COUNT = 9


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientPartitionStream:
    client_id: ClientId
    source_row_identity: DatasetSourceIdentity
    stream: ParquetBatchStream


@dataclass(frozen=True, slots=True, kw_only=True)
class NaturalDevicePartitioner:
    raw_root: Path
    materialized_root: Path
    artifact_store: FileArtifactStore
    streaming_chunk_policy: StreamingChunkPolicy

    def partition(self, request: ClientPartitionRequest) -> ClientPartitionResult:
        if type(request.partitioning) is not NaturalDevicePartitionSpec:
            raise _partition_error("natural-device partitioner requires a NaturalDevicePartitionSpec")
        device_ids = tuple(path.name for path in sorted_device_directories(self.raw_root))
        if len(device_ids) != _REGIME_A_DEVICE_COUNT:
            raise _partition_error(
                f"natural-device partitioning requires exactly {_REGIME_A_DEVICE_COUNT} physical devices, "
                f"found {len(device_ids)}"
            )
        adapter = NBaIoTChunkedSourceAdapter(
            raw_root=self.raw_root,
            output_root=self.materialized_root,
            csv_block_bytes=self.streaming_chunk_policy.csv_block_bytes.value,
        )
        memberships: list[ClientRowMembership] = []
        for device_id in device_ids:
            materialization = adapter.materialize_device(device_id)
            memberships.append(
                ClientRowMembership(
                    client_id=ClientId(value=device_id),
                    row_count=materialization.row_count,
                    row_order_checksum=materialization.row_order_checksum,
                )
            )
        ordered_client_ids = sorted(
            (membership.client_id for membership in memberships), key=lambda client_id: client_id.value
        )
        roster = ClientRoster(client_ids=tuple(ordered_client_ids))
        manifest = ClientPartitionManifest(
            dataset=Dataset.N_BAIOT,
            strategy=request.partitioning.strategy,
            source_row_identity=request.inspection.source_row_identity,
            client_roster=roster,
            client_row_memberships=tuple(memberships),
        )
        content = msgspec.json.encode(manifest)
        content_hash = blake3_bytes_content_hash(content)
        artifact = ArtifactRef(
            artifact_id=ArtifactId(value=f"artifact-{content_hash}"),
            artifact_type=ArtifactType.PARTITION_MANIFEST,
            content_hash=content_hash,
            schema_version=ArtifactSchemaVersion(value="v1"),
            serialization_format=SerializationFormat.JSON,
        )
        key = DatasetArtifactKey(
            artifact_type=ArtifactType.PARTITION_MANIFEST,
            dataset=Dataset.N_BAIOT,
            stage_identity=StageFingerprint(value=content_hash),
            namespace=ArtifactNamespace.DATP_ANCHOR,
        )
        write_result = self.artifact_store.write_atomically(
            WriteArtifactRequest(
                key=key, artifact=artifact, content=content, write_disposition=WriteDisposition.CREATE_IF_ABSENT
            )
        )
        return ClientPartitionResult(
            partition_manifest=write_result.artifact,
            client_roster=roster,
            partition_identity=PartitionIdentity(value=StageFingerprint(value=content_hash)),
        )


def _partition_error(coverage: str) -> PartitionError:
    return PartitionError(dataset="n_baiot", regime="a", coverage=coverage, detail=coverage)


def stable_client_partition_order(
    partitions: tuple[ClientPartitionStream, ...],
) -> tuple[ClientPartitionStream, ...]:
    client_ids = tuple(partition.client_id for partition in partitions)
    if len(set(client_ids)) != len(client_ids):
        duplicate = next(client_id for client_id in client_ids if client_ids.count(client_id) > 1)
        raise PartitionError(
            dataset="unresolved",
            regime="unresolved",
            coverage=duplicate.value,
            detail="each client must have exactly one partition source stream",
        )
    return tuple(sorted(partitions, key=lambda partition: partition.client_id.value))
