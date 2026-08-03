"""Filesystem layout for reusable processed-data assets."""

from enum import StrEnum
from pathlib import Path

from datp_core.artifacts.coordinates import (
    ReusableDataCoordinate,
    federated_client_coordinate,
    processed_branch_coordinate,
)
from datp_core.domain.enums import PartitionRole, ProcessedDataBranch, SplitProtocolId
from datp_core.domain.values import ClientPathToken


class ProcessedAssetName(StrEnum):
    TRAIN = f"{PartitionRole.TRAIN}.parquet"
    CALIBRATION = f"{PartitionRole.CALIBRATION}.parquet"
    EVALUATION = f"{PartitionRole.EVALUATION}.parquet"
    FUTURE_RECALIBRATION = f"{PartitionRole.FUTURE_RECALIBRATION}.parquet"
    STATIC_REFERENCE_RESERVE = f"{PartitionRole.STATIC_REFERENCE_RESERVE}.parquet"
    STATE = "state.skops"
    SCHEMA = "schema.json"
    SPLIT_MANIFEST = "split_manifest.parquet"
    PREPROCESSING_MANIFEST = "preprocessing_manifest.json"
    COMPLETE = "COMPLETE"
    VALIDATION_REPORT = "validation_report.json"


def asset_for_partition(role: PartitionRole) -> ProcessedAssetName:
    match role:
        case PartitionRole.TRAIN:
            return ProcessedAssetName.TRAIN
        case PartitionRole.CALIBRATION:
            return ProcessedAssetName.CALIBRATION
        case PartitionRole.EVALUATION:
            return ProcessedAssetName.EVALUATION
        case PartitionRole.FUTURE_RECALIBRATION:
            return ProcessedAssetName.FUTURE_RECALIBRATION
        case PartitionRole.STATIC_REFERENCE_RESERVE:
            return ProcessedAssetName.STATIC_REFERENCE_RESERVE


def processed_asset_names(split_protocol: SplitProtocolId) -> tuple[ProcessedAssetName, ...]:
    """Every persisted partition is declared by its split protocol."""
    partition_assets = tuple(asset_for_partition(role) for role in partition_roles(split_protocol))
    return (
        *partition_assets,
        ProcessedAssetName.STATE,
        ProcessedAssetName.SCHEMA,
        ProcessedAssetName.PREPROCESSING_MANIFEST,
        ProcessedAssetName.VALIDATION_REPORT,
        ProcessedAssetName.COMPLETE,
    )


def core_processed_asset_names() -> tuple[ProcessedAssetName, ...]:
    """The non-temporal core artifact inventory used by common consumers."""
    return processed_asset_names(SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS)


def partition_roles(split_protocol: SplitProtocolId) -> tuple[PartitionRole, ...]:
    match split_protocol:
        case SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS:
            return (PartitionRole.TRAIN, PartitionRole.CALIBRATION, PartitionRole.EVALUATION)
        case SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE:
            return (
                PartitionRole.TRAIN,
                PartitionRole.CALIBRATION,
                PartitionRole.FUTURE_RECALIBRATION,
                PartitionRole.EVALUATION,
            )
        case SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE:
            return (
                PartitionRole.TRAIN,
                PartitionRole.CALIBRATION,
                PartitionRole.STATIC_REFERENCE_RESERVE,
                PartitionRole.EVALUATION,
            )


def scored_partition_roles(split_protocol: SplitProtocolId) -> tuple[PartitionRole, ...]:
    """Post-training partitions that are legitimate detector score inputs."""
    return tuple(
        role
        for role in partition_roles(split_protocol)
        if role not in {PartitionRole.TRAIN, PartitionRole.STATIC_REFERENCE_RESERVE}
    )


def federated_branch_directory(data_root: Path, coordinate: ReusableDataCoordinate) -> Path:
    if coordinate.branch is not ProcessedDataBranch.FEDERATED:
        raise ValueError("federated branch directory requires the federated branch")
    return processed_branch_coordinate(data_root, coordinate)


def centralized_branch_directory(data_root: Path, coordinate: ReusableDataCoordinate) -> Path:
    if coordinate.branch is not ProcessedDataBranch.CENTRALIZED_REFERENCE:
        raise ValueError("centralized branch directory requires the centralized-reference branch")
    return processed_branch_coordinate(data_root, coordinate)


def federated_client_directory(data_root: Path, coordinate: ReusableDataCoordinate) -> Path:
    return federated_client_coordinate(data_root, coordinate)


def client_asset_path(client_directory: Path, asset: ProcessedAssetName) -> Path:
    return client_directory / asset.value


def branch_asset_path(branch_directory: Path, asset: ProcessedAssetName) -> Path:
    return branch_directory / asset.value


def canonical_relative_asset_path(
    asset: ProcessedAssetName,
    branch: ProcessedDataBranch,
    client_identity: ClientPathToken | None = None,
) -> str:
    if branch is ProcessedDataBranch.FEDERATED:
        if client_identity is None:
            raise ValueError("federated relative asset path requires a client identity")
        return f"{client_identity.value}/{asset.value}"
    if client_identity is not None:
        raise ValueError("centralized relative asset path must not specify a client identity")
    return asset.value
