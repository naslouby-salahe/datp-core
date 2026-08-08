from pathlib import Path

import polars as pl
import pytest

from datp_core.core.identifiers import DatasetId, PopulationId, SplitProtocolId
from datp_core.core.numeric import Seed
from datp_core.data.nbaiot.populations import construct_nbaiot_natural_devices
from datp_core.data.populations.contracts import SplitConstructionRequest
from datp_core.data.populations.splits import split_membership


@pytest.mark.parametrize("seed", [Seed(0), Seed(1), Seed(2), Seed(3), Seed(4), Seed(5), Seed(6), Seed(7)])
def test_non_temporal_splits_are_disjoint_for_any_seed(seed: Seed, nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=seed, split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    assignments, _ = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=seed,
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    assert assignments.get_column("stable_row_id").n_unique() == assignments.height
    assert assignments.height == membership.height
    train_cal = assignments.filter(pl.col("partition_role").is_in(["train", "calibration"]))
    assert train_cal.filter(pl.col("outcome_label") == "attack").height == 0
