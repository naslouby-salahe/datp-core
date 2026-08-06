"""Preprocessing coordinates, persisted asset identities, and deterministic paths."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from datp_core.domain.enums import (
    DatasetId,
    PartitionRole,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    ReusableDataCoordinateKind,
    SplitProtocolId,
)
from datp_core.domain.values.base import sequence_pydantic_schema, str_subclass_schema, validate_non_empty_tuple
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.paths import ClientPathToken


class PreprocessingFitScope(StrEnum):
    CLIENT_LOCAL_TRAINING = "client_local_training"
    POOLED_TRAINING = "pooled_training"


class TrustedEstimatorClassName(StrEnum):
    STANDARD_SCALER = "standard_scaler"
    MIN_MAX_SCALER = "min_max_scaler"


class PartitionOrdering(StrEnum):
    PRESERVE_SOURCE_ORDER = "preserve_source_order"
    STABLE_ROW_ID = "stable_row_id"


@dataclass(frozen=True, slots=True)
class ReusableDataCoordinate:
    dataset: DatasetId
    population: PopulationId
    partition_seed: Seed
    split_protocol_identity: SplitProtocolId
    preprocessing_identity: PreprocessingProtocolId
    branch: ProcessedDataBranch
    client_identity: ClientPathToken | None

    def __post_init__(self) -> None:
        if self.branch is ProcessedDataBranch.CENTRALIZED_REFERENCE and self.client_identity is not None:
            raise ValueError("centralized reusable coordinates cannot include client identity")


class RelativeAssetPath(str):
    def __new__(cls, value: "str | RelativeAssetPath") -> "RelativeAssetPath":
        path_text = str(value)
        if not path_text:
            raise ValueError("relative asset path must be a non-empty string")
        if "=" in path_text:
            raise ValueError("reusable data paths must not contain key=value segments")
        if Path(path_text).is_absolute():
            raise ValueError("relative asset path must not be absolute")
        return super().__new__(cls, path_text)

    __get_pydantic_core_schema__ = classmethod(str_subclass_schema)


@dataclass(frozen=True, slots=True)
class RelativeAssetPathSequence:
    paths: tuple[RelativeAssetPath, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.paths, tuple):
            raise TypeError("relative asset paths must be an immutable tuple")
        wrapped = tuple(item if isinstance(item, RelativeAssetPath) else RelativeAssetPath(item) for item in self.paths)
        object.__setattr__(self, "paths", wrapped)
        validate_non_empty_tuple(self.paths, "relative asset path sequence")

    def __len__(self) -> int:
        return len(self.paths)

    def __iter__(self):
        return iter(self.paths)

    __get_pydantic_core_schema__ = classmethod(sequence_pydantic_schema)


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


def processed_root_under(data_root: Path, coordinate: ReusableDataCoordinate) -> Path:
    return (
        data_root
        / ReusableDataCoordinateKind.PROCESSED
        / coordinate.dataset.value
        / coordinate.population.value
        / str(coordinate.partition_seed.value)
        / coordinate.split_protocol_identity.value
        / coordinate.preprocessing_identity.value
    )


def processed_branch_coordinate(data_root: Path, coordinate: ReusableDataCoordinate) -> Path:
    return processed_root_under(data_root, coordinate) / coordinate.branch.value


def federated_client_coordinate(data_root: Path, coordinate: ReusableDataCoordinate) -> Path:
    if coordinate.branch is not ProcessedDataBranch.FEDERATED:
        raise ValueError("only federated coordinates may include client identity")
    if coordinate.client_identity is None:
        raise ValueError("federated client coordinates require a client identity")
    return processed_branch_coordinate(data_root, coordinate) / coordinate.client_identity.value


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
    return tuple(
        role
        for role in partition_roles(split_protocol)
        if role not in {PartitionRole.TRAIN, PartitionRole.STATIC_REFERENCE_RESERVE}
    )


def processed_asset_names(split_protocol: SplitProtocolId) -> tuple[ProcessedAssetName, ...]:
    return (
        *(asset_for_partition(role) for role in partition_roles(split_protocol)),
        ProcessedAssetName.STATE,
        ProcessedAssetName.SCHEMA,
        ProcessedAssetName.PREPROCESSING_MANIFEST,
        ProcessedAssetName.VALIDATION_REPORT,
        ProcessedAssetName.COMPLETE,
    )


def core_processed_asset_names() -> tuple[ProcessedAssetName, ...]:
    return processed_asset_names(SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS)


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
