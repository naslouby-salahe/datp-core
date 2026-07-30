"""Deterministic reusable-data coordinates without key=value path segments."""

from dataclasses import dataclass
from pathlib import Path

from datp_core.domain.enums import (
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    RawDatasetDirectory,
    ReusableDataCoordinateKind,
    SplitProtocolId,
)
from datp_core.domain.values import ClientPathToken, Seed
from datp_core.protocols.runtime import DATA_ROOT


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


def raw_dataset_directory(dataset: DatasetId) -> RawDatasetDirectory:
    return RawDatasetDirectory[dataset.name]


def raw_dataset_root(dataset: DatasetId) -> Path:
    return DATA_ROOT / ReusableDataCoordinateKind.RAW / raw_dataset_directory(dataset).value


def canonical_root_under(data_root: Path, dataset: DatasetId) -> Path:
    return data_root / ReusableDataCoordinateKind.CANONICAL / dataset.value


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
