from dataclasses import replace
from pathlib import Path

import pytest

from datp_core.domain.enums import (
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SplitProtocolId,
)
from datp_core.domain.values.counts import Seed
from datp_core.domain.values.paths import ClientPathToken
from datp_core.preprocessing.contracts import (
    PartitionOrdering,
    PreprocessingFitScope,
    ProcessedAssetName,
    ReusableDataCoordinate,
    TrustedEstimatorClassName,
    centralized_branch_directory,
    core_processed_asset_names,
    federated_branch_directory,
    federated_client_coordinate,
    federated_client_directory,
    processed_branch_coordinate,
)


def test_preprocessing_identity_enum_member_sets_are_exact_and_unique() -> None:
    cases = (
        (PreprocessingFitScope, {"CLIENT_LOCAL_TRAINING", "POOLED_TRAINING"}),
        (TrustedEstimatorClassName, {"STANDARD_SCALER", "MIN_MAX_SCALER"}),
        (PartitionOrdering, {"PRESERVE_SOURCE_ORDER", "STABLE_ROW_ID"}),
    )
    for enum_type, expected_members in cases:
        assert set(enum_type.__members__) == expected_members
        values = tuple(member.value for member in enum_type)
        assert len(values) == len(set(values))
        assert all(value.islower() for value in values)


def _coordinate(
    branch: ProcessedDataBranch = ProcessedDataBranch.FEDERATED,
    client: ClientPathToken | None = None,
) -> ReusableDataCoordinate:
    return ReusableDataCoordinate(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(1),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        branch=branch,
        client_identity=client,
    )


def test_processed_coordinates_match_approved_layout() -> None:
    data_root = Path("data")
    path = processed_branch_coordinate(data_root, _coordinate())
    assert path == Path(
        "data/processed/nbaiot/nbaiot_natural_devices/1/"
        f"{SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS.value}/"
        f"{PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION.value}/"
        "no_controlled_partition/federated"
    )
    coordinate = replace(_coordinate(), client_identity=ClientPathToken("danmini_doorbell"))
    client = federated_client_coordinate(data_root, coordinate)
    assert client.parts[-1] == "danmini_doorbell"
    assert "client" not in client.parts
    with pytest.raises(ValueError):
        ClientPathToken("client=bad")


def test_layout_separates_federated_and_centralized_branches() -> None:
    data_root = Path("data")
    federated = federated_branch_directory(data_root, _coordinate(ProcessedDataBranch.FEDERATED))
    centralized = centralized_branch_directory(data_root, _coordinate(ProcessedDataBranch.CENTRALIZED_REFERENCE))
    client = federated_client_directory(
        data_root, _coordinate(ProcessedDataBranch.FEDERATED, ClientPathToken("device_a"))
    )
    assert federated.name == ProcessedDataBranch.FEDERATED.value
    assert centralized.name == ProcessedDataBranch.CENTRALIZED_REFERENCE.value
    assert client.name == "device_a"
    assert "client" not in client.parts
    assert ProcessedAssetName.STATE == "state.skops"
    assert ProcessedAssetName.TRAIN in core_processed_asset_names()
    assert "=" not in str(federated)
