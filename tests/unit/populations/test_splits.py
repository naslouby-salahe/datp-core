from pathlib import Path

import polars as pl

from datp_core.domain.enums import DatasetId, PartitionRole, PopulationId, SplitProtocolId
from datp_core.domain.values import Seed
from datp_core.populations.models import SplitConstructionRequest
from datp_core.populations.nbaiot_natural_devices import build_nbaiot_natural_devices
from datp_core.populations.splits import split_membership


def test_non_temporal_equal_thirds_are_disjoint_and_benign_only_for_train_cal(
    nbaiot_canonical_root: Path,
) -> None:
    manifest, membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
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
        split_manifest.document.train_row_count
        + split_manifest.document.calibration_row_count
        + (split_manifest.document.evaluation_row_count)
        == assignments.height
    )


def test_attack_rows_never_enter_training(nbaiot_canonical_root: Path) -> None:
    manifest, membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(1), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
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
    manifest, membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(5), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    first, first_manifest = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=Seed(5),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    second, second_manifest = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=Seed(5),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    assert first.equals(second)
    assert first_manifest.document.assignment_checksum == second_manifest.document.assignment_checksum


def test_row_cannot_appear_in_two_splits(nbaiot_canonical_root: Path) -> None:
    manifest, membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
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
