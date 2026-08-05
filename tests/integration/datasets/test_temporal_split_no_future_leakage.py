from datetime import datetime
from pathlib import Path

import polars as pl

from datp_core.datasets.edge_iiotset.populations import construct_edge_temporal_groups
from datp_core.datasets.partitioning.contracts import SplitConstructionRequest
from datp_core.datasets.partitioning.integrity import validate_no_future_history_leakage
from datp_core.datasets.partitioning.splits import split_membership
from datp_core.domain.enums import DatasetId, PartitionRole, PopulationId, SplitProtocolId
from datp_core.domain.values import Seed


def test_temporal_split_preserves_history_before_future(edge_temporal_eligible_root: Path) -> None:
    construction = construct_edge_temporal_groups(
        edge_temporal_eligible_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    )
    manifest, membership = construction.manifest, construction.membership
    assignments, split_manifest = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.EDGE_TEMPORAL_GROUPS,
            dataset=DatasetId.EDGE_IIOTSET,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
            population_manifest_checksum=manifest.document.membership_checksum,
            capture_timestamp_column="capture_timestamp",
        )
    )
    assert split_manifest.split_protocol is SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE
    assert assignments.height == membership.height
    validate_no_future_history_leakage(assignments, "capture_timestamp")
    historical = assignments.filter(
        pl.col("partition_role").is_in([PartitionRole.TRAIN.value, PartitionRole.CALIBRATION.value])
    )
    future = assignments.filter(
        pl.col("partition_role").is_in([PartitionRole.FUTURE_RECALIBRATION.value, PartitionRole.EVALUATION.value])
    )
    assert historical.height > 0
    assert future.height > 0
    for client_id in membership.get_column("client_id").unique().to_list():
        hist_max = historical.filter(pl.col("client_id") == client_id).get_column("capture_timestamp").max()
        fut_min = future.filter(pl.col("client_id") == client_id).get_column("capture_timestamp").min()
        assert isinstance(hist_max, datetime)
        assert isinstance(fut_min, datetime)
        assert hist_max <= fut_min
