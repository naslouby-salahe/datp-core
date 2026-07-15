from datp_core.application.ports.data import ClientPartitioner, ClientPartitionRequest
from datp_core.domain.data.datasets import DatasetSourceInspectionResult
from datp_core.domain.data.partitioning import ClientPartitionResult, ClientPartitionSpec


def partition_clients(
    *, partitioner: ClientPartitioner, inspection: DatasetSourceInspectionResult, partitioning: ClientPartitionSpec
) -> ClientPartitionResult:
    return partitioner.partition(ClientPartitionRequest(inspection=inspection, partitioning=partitioning))
