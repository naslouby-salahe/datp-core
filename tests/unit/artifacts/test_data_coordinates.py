from dataclasses import replace
from pathlib import Path

import pytest

from datp_core.artifacts.coordinates import (
    ReusableDataCoordinate,
    federated_client_coordinate,
    processed_branch_coordinate,
    raw_dataset_directory,
    raw_dataset_root,
)
from datp_core.domain.enums import (
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    RawDatasetDirectory,
    SplitProtocolId,
)
from datp_core.domain.values import ClientPathToken, Seed


def _base_coordinate() -> ReusableDataCoordinate:
    return ReusableDataCoordinate(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        branch=ProcessedDataBranch.FEDERATED,
        client_identity=None,
    )


def test_processed_coordinates_match_approved_layout() -> None:
    data_root = Path("data")
    path = processed_branch_coordinate(data_root, _base_coordinate())
    assert path == Path(
        "data/processed/nbaiot/nbaiot_natural_devices/0/"
        f"{SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS.value}/"
        f"{PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION.value}/federated"
    )
    coordinate = replace(_base_coordinate(), client_identity=ClientPathToken("danmini_doorbell"))
    client = federated_client_coordinate(data_root, coordinate)
    assert client.parts[-1] == "danmini_doorbell"
    assert "client" not in client.parts
    with pytest.raises(ValueError):
        ClientPathToken("client=bad")


def test_raw_dataset_directories_are_enum_backed() -> None:
    assert raw_dataset_directory(DatasetId.NBAIOT) is RawDatasetDirectory.NBAIOT
    assert raw_dataset_root(DatasetId.CICIOT2023) == Path(f"data/raw/{RawDatasetDirectory.CICIOT2023.value}")
    assert raw_dataset_directory(DatasetId.EDGE_IIOTSET) is RawDatasetDirectory.EDGE_IIOTSET
