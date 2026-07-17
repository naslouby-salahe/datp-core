from dataclasses import dataclass

from datp_core.domain.artifacts.lineage import DatasetSourceIdentity
from datp_core.domain.errors import PartitionError
from datp_core.domain.experiments.identities import ClientId
from datp_core.infrastructure.data.streaming import ParquetBatchStream


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientPartitionStream:
    client_id: ClientId
    source_row_identity: DatasetSourceIdentity
    stream: ParquetBatchStream


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
