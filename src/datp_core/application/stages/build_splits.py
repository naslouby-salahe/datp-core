from datp_core.application.ports.data import BuildSplitManifestRequest, SplitManifestBuilder
from datp_core.domain.data.partitioning import ClientPartitionResult
from datp_core.domain.data.splitting import SplitCollectionSpec, SplitManifestResult


def build_splits(
    *, builder: SplitManifestBuilder, partition: ClientPartitionResult, splits: SplitCollectionSpec
) -> SplitManifestResult:
    return builder.build(BuildSplitManifestRequest(partition=partition, splits=splits))
