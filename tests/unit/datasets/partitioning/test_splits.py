from pathlib import Path

import polars as pl
import pytest

from datp_core.core.identifiers import DatasetId, PartitionRole, PopulationId, SplitProtocolId
from datp_core.core.numeric import RowCount, Seed
from datp_core.data.nbaiot.populations import construct_nbaiot_natural_devices
from datp_core.data.populations.contracts import SplitConstructionRequest
from datp_core.data.populations.splits import hamilton_integer_counts, split_membership


def test_hamilton_allocation_conserves_rows_and_is_deterministic() -> None:
    assert hamilton_integer_counts(RowCount(10), (1 / 3, 1 / 3, 1 / 3)) == (
        RowCount(4),
        RowCount(3),
        RowCount(3),
    )
    assert hamilton_integer_counts(RowCount(11), (1 / 3, 1 / 3, 1 / 3)) == (
        RowCount(4),
        RowCount(4),
        RowCount(3),
    )
    temporal = hamilton_integer_counts(RowCount(100), (0.55, 0.15, 0.10, 0.20))
    assert sum(count.value for count in temporal) == 100
    assert temporal == (RowCount(55), RowCount(15), RowCount(10), RowCount(20))


def test_hamilton_rejects_invalid_ratios() -> None:
    row_count = RowCount(10)
    with pytest.raises(ValueError):
        hamilton_integer_counts(row_count, (0.5, 0.5, 0.5))
    with pytest.raises(ValueError):
        hamilton_integer_counts(row_count, (1.5,))


def test_non_temporal_equal_thirds_are_disjoint_and_benign_only_for_train_cal(
    nbaiot_canonical_root: Path,
) -> None:
    construction = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    assignments, split_manifest = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    assert assignments.height == membership.height
    assert assignments.get_column("stable_row_id").n_unique() == assignments.height
    train_cal = assignments.filter(
        pl.col("partition_role").is_in([PartitionRole.TRAIN.value, PartitionRole.CALIBRATION.value])
    )
    assert train_cal.filter(pl.col("outcome_label") == "attack").height == 0
    assert (
        split_manifest.train_row_count.plus(split_manifest.calibration_row_count)
        .plus(split_manifest.evaluation_row_count)
        .value
        == assignments.height
    )


def test_attack_rows_never_enter_training(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(1), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    assignments, _ = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=Seed(1),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    attacks_in_train = assignments.filter(
        (pl.col("partition_role") == PartitionRole.TRAIN.value) & (pl.col("outcome_label") == "attack")
    )
    assert attacks_in_train.height == 0


def test_split_is_deterministic_for_fixed_seed(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(5), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    request = SplitConstructionRequest(
        membership=membership,
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        partition_seed=Seed(5),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        population_manifest_checksum=manifest.document.membership_checksum,
    )
    first, first_manifest = split_membership(request)
    second, second_manifest = split_membership(request)
    assert first.equals(second)
    assert first_manifest.assignment_checksum == second_manifest.assignment_checksum


def test_row_cannot_appear_in_two_splits(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    assignments, _ = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    duplicated = assignments.group_by("stable_row_id").len().filter(pl.col("len") > 1)
    assert duplicated.height == 0
