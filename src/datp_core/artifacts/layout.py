"""Filesystem layout for reusable processed-data assets."""

from enum import StrEnum
from pathlib import Path

from datp_core.artifacts.coordinates import (
    ReusableDataCoordinate,
    federated_client_coordinate,
    processed_branch_coordinate,
)
from datp_core.domain.enums import PartitionRole, ProcessedDataBranch


class ProcessedAssetName(StrEnum):
    TRAIN = f"{PartitionRole.TRAIN}.parquet"
    CALIBRATION = f"{PartitionRole.CALIBRATION}.parquet"
    EVALUATION = f"{PartitionRole.EVALUATION}.parquet"
    FUTURE_RECALIBRATION = f"{PartitionRole.FUTURE_RECALIBRATION}.parquet"
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


def core_processed_asset_names() -> tuple[ProcessedAssetName, ...]:
    return (
        ProcessedAssetName.TRAIN,
        ProcessedAssetName.CALIBRATION,
        ProcessedAssetName.EVALUATION,
        ProcessedAssetName.STATE,
        ProcessedAssetName.SCHEMA,
        ProcessedAssetName.PREPROCESSING_MANIFEST,
        ProcessedAssetName.VALIDATION_REPORT,
        ProcessedAssetName.COMPLETE,
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
