from pathlib import Path

import polars as pl
import pytest

from datp_core.domain.enums import DatasetId, PopulationId, SplitProtocolId
from datp_core.domain.values import Seed
from datp_core.populations.models import SplitConstructionRequest
from datp_core.populations.nbaiot_natural_devices import build_nbaiot_natural_devices
from datp_core.populations.splits import split_membership


@pytest.mark.parametrize("seed", range(8))
def test_non_temporal_splits_are_disjoint_for_any_seed(seed: int, nbaiot_canonical_root: Path) -> None:
    manifest, membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(seed), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    assignments, _ = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=Seed(seed),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    assert assignments.get_column("stable_row_id").n_unique() == assignments.height
    assert assignments.height == membership.height
    train_cal = assignments.filter(pl.col("partition_role").is_in(["train", "calibration"]))
    assert train_cal.filter(pl.col("outcome_label") == "attack").height == 0
