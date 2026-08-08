"""Shared PreprocessedPartitionPaths construction for federated and centralized publication."""

from pathlib import Path

from datp_core.data.preprocessing.artifacts import asset_for_partition, client_asset_path, partition_roles
from datp_core.data.preprocessing.models import PreprocessedPartitionPaths
from datp_core.domain.enums import PartitionRole, SplitProtocolId


def build_preprocessed_partition_paths(
    coordinate_directory: Path,
    split_protocol: SplitProtocolId,
) -> PreprocessedPartitionPaths:
    paths_by_role = {
        role: client_asset_path(coordinate_directory, asset_for_partition(role))
        for role in partition_roles(split_protocol)
    }
    return PreprocessedPartitionPaths(
        train=paths_by_role[PartitionRole.TRAIN],
        calibration=paths_by_role[PartitionRole.CALIBRATION],
        evaluation=paths_by_role[PartitionRole.EVALUATION],
        future_recalibration=paths_by_role.get(PartitionRole.FUTURE_RECALIBRATION),
        static_reference_reserve=paths_by_role.get(PartitionRole.STATIC_REFERENCE_RESERVE),
    )
