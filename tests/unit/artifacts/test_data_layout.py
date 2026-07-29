from datp_core.artifacts.layout import (
    ProcessedAssetName,
    centralized_branch_directory,
    core_processed_asset_names,
    federated_branch_directory,
    federated_client_directory,
)
from datp_core.domain.enums import (
    DatasetId,
    PopulationId,
    PreprocessingProtocolId,
    ProcessedDataBranch,
    SplitProtocolId,
)
from datp_core.domain.values import Seed
from datp_core.preprocessing.models import ReusableDataCoordinate


def _coordinate(branch: ProcessedDataBranch, client: str | None = None) -> ReusableDataCoordinate:
    return ReusableDataCoordinate(
        dataset=DatasetId.NBAIOT,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(1),
        split_protocol_identity=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        preprocessing_identity=PreprocessingProtocolId.TEST_COLUMN_ORDER_PROJECTION,
        branch=branch,
        client_identity=client,
    )


def test_layout_separates_federated_and_centralized_branches() -> None:
    federated = federated_branch_directory(_coordinate(ProcessedDataBranch.FEDERATED))
    centralized = centralized_branch_directory(_coordinate(ProcessedDataBranch.CENTRALIZED_REFERENCE))
    client = federated_client_directory(_coordinate(ProcessedDataBranch.FEDERATED, "device_a"))
    assert federated.name == ProcessedDataBranch.FEDERATED.value
    assert centralized.name == ProcessedDataBranch.CENTRALIZED_REFERENCE.value
    assert client.name == "device_a"
    assert "client" not in client.parts
    assert ProcessedAssetName.STATE == "state.skops"
    assert ProcessedAssetName.TRAIN in core_processed_asset_names()
    assert "=" not in str(federated)
