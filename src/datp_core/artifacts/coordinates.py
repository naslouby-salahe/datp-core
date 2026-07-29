"""Deterministic reusable-data coordinates without key=value path segments."""

from pathlib import Path

from datp_core.domain.enums import DatasetId, ProcessedDataBranch, RawDatasetDirectory, ReusableDataCoordinateKind
from datp_core.preprocessing.models import ReusableDataCoordinate
from datp_core.protocols.models import DATA_ROOT


def assert_descriptive_segment(segment: str, subject: str) -> str:
    invalid_reason = _descriptive_segment_failure(segment)
    if invalid_reason is not None:
        raise ValueError(f"{subject} {invalid_reason}")
    return segment


def _descriptive_segment_failure(segment: str) -> str | None:
    if not segment:
        return "must be a non-empty path segment"
    if segment in {".", ".."}:
        return "must not be a relative path token"
    if "=" in segment:
        return "must not use key=value path syntax"
    if "/" in segment or "\\" in segment:
        return "must be a single path segment"
    return None


def raw_dataset_directory(dataset: DatasetId) -> RawDatasetDirectory:
    return RawDatasetDirectory[dataset.name]


def raw_dataset_root(dataset: DatasetId) -> Path:
    return DATA_ROOT / ReusableDataCoordinateKind.RAW / raw_dataset_directory(dataset).value


def canonical_dataset_coordinate(dataset: DatasetId) -> Path:
    return DATA_ROOT / ReusableDataCoordinateKind.CANONICAL / dataset.value


def processed_root_coordinate(coordinate: ReusableDataCoordinate) -> Path:
    return (
        DATA_ROOT
        / ReusableDataCoordinateKind.PROCESSED
        / coordinate.dataset.value
        / coordinate.population.value
        / str(coordinate.partition_seed.value)
        / assert_descriptive_segment(coordinate.split_protocol_identity.value, "split_protocol_identity")
        / assert_descriptive_segment(coordinate.preprocessing_identity.value, "preprocessing_identity")
    )


def processed_branch_coordinate(coordinate: ReusableDataCoordinate) -> Path:
    return processed_root_coordinate(coordinate) / coordinate.branch.value


def federated_client_coordinate(coordinate: ReusableDataCoordinate) -> Path:
    if coordinate.branch is not ProcessedDataBranch.FEDERATED:
        raise ValueError("only federated coordinates may include client identity")
    if coordinate.client_identity is None:
        raise ValueError("federated client coordinates require a client identity")
    return processed_branch_coordinate(coordinate) / assert_descriptive_segment(
        coordinate.client_identity, "client_identity"
    )


def reusable_coordinate_path(coordinate: ReusableDataCoordinate) -> Path:
    if coordinate.client_identity is None:
        return processed_branch_coordinate(coordinate)
    return federated_client_coordinate(coordinate)


def path_contains_key_value_segment(path: Path) -> bool:
    return any("=" in part for part in path.parts)
