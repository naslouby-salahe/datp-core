from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.artifacts.coordinates import (
    ReusableDataCoordinate,
    federated_client_coordinate,
    processed_branch_coordinate,
)
from datp_core.domain.enums import PartitionRole, ProcessedDataBranch, SplitProtocolId
from datp_core.domain.values import (
    ClientPathToken,
    _sequence_pydantic_schema,
    _str_subclass_schema,
    _validate_non_empty_tuple,
)


class RelativeAssetPath(str):
    def __new__(cls, value: "str | RelativeAssetPath") -> "RelativeAssetPath":
        val_str = str(value)

        if not val_str or not isinstance(val_str, str):
            raise ValueError("relative asset path must be a non-empty string")
        if "=" in val_str:
            raise ValueError("reusable data paths must not contain key=value segments")
        if Path(val_str).is_absolute():
            raise ValueError("relative asset path must not be absolute")
        return super().__new__(cls, val_str)

    __get_pydantic_core_schema__ = classmethod(_str_subclass_schema)


@dataclass(frozen=True, slots=True)
class RelativeAssetPathSequence:
    paths: tuple[RelativeAssetPath, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.paths, tuple):
            raise TypeError("relative asset paths must be an immutable tuple")
        wrapped = tuple(item if isinstance(item, RelativeAssetPath) else RelativeAssetPath(item) for item in self.paths)
        object.__setattr__(self, "paths", wrapped)
        _validate_non_empty_tuple(self.paths, "relative asset path sequence")

    def __len__(self) -> int:
        return len(self.paths)

    def __iter__(self):
        return iter(self.paths)

    __get_pydantic_core_schema__ = classmethod(_sequence_pydantic_schema)


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
) -> RelativeAssetPath:
    if branch is ProcessedDataBranch.FEDERATED:
        if client_identity is None:
            raise ValueError("federated relative asset path requires a client identity")
        return RelativeAssetPath(f"{client_identity.value}/{asset.value}")
    if client_identity is not None:
        raise ValueError("centralized relative asset path must not specify a client identity")
    return RelativeAssetPath(asset.value)
