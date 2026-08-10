from pathlib import Path

import polars as pl
import pytest

from datp_core.artifacts.provenance import Checksum
from datp_core.core.errors import DataIntegrityError, LeakageError
from datp_core.core.identifiers import DatasetId, PartitionRole, PopulationId, SplitProtocolId
from datp_core.core.numeric import RowCount, Seed
from datp_core.data.nbaiot.populations import construct_nbaiot_natural_devices
from datp_core.data.populations.contracts import SplitConstructionRequest, SplitManifestDocument
from datp_core.data.populations.integrity import (
    outcome_row_counts,
    validate_population_manifest,
    validate_split_manifest,
)
from datp_core.data.populations.splits import split_membership
from datp_core.data.registry import population_capabilities, population_declaration


def test_outcome_row_counts_preserves_outcome_semantics() -> None:
    counts = outcome_row_counts(
        pl.DataFrame(
            {
                "outcome_label": ["benign", "attack", "benign"],
            }
        )
    )

    assert counts.benign_row_count == RowCount(2)
    assert counts.attack_row_count == RowCount(1)


def test_integrity_accepts_valid_population_and_split(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    validate_population_manifest(
        manifest,
        membership,
        population_declaration(PopulationId.NBAIOT_NATURAL_DEVICES),
        population_capabilities(PopulationId.NBAIOT_NATURAL_DEVICES),
    )
    split = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    validate_split_manifest(membership, split.assignments, split.manifest)


def test_integrity_detects_duplicate_split_assignment(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    split = split_membership(
        SplitConstructionRequest(
            membership=membership,
            population=PopulationId.NBAIOT_NATURAL_DEVICES,
            dataset=DatasetId.NBAIOT,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            population_manifest_checksum=manifest.document.membership_checksum,
        )
    )
    poisoned = pl.concat([split.assignments, split.assignments.head(1)])
    with pytest.raises(DataIntegrityError):
        validate_split_manifest(membership, poisoned, split.manifest)


def test_integrity_detects_attack_in_calibration() -> None:
    membership = pl.DataFrame(
        {
            "client_id": ["c0", "c0"],
            "stable_row_id": ["r0", "r1"],
            "outcome_label": ["benign", "attack"],
            "source_path": ["a", "b"],
            "source_row_index": [0, 1],
        }
    )
    assignments = membership.with_columns(pl.lit(PartitionRole.CALIBRATION.value).alias("partition_role"))
    document = SplitManifestDocument(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        dataset=DatasetId.NBAIOT,
        partition_seed=Seed(0),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        assignment_row_count=RowCount(2),
        train_row_count=RowCount(0),
        calibration_row_count=RowCount(2),
        evaluation_row_count=RowCount(0),
        future_recalibration_row_count=RowCount(0),
        static_reference_reserve_row_count=RowCount(0),
        discarded_row_count=RowCount(0),
        assignment_checksum=Checksum("b" * 64),
        population_manifest_checksum=Checksum("c" * 64),
    )
    with pytest.raises(LeakageError):
        validate_split_manifest(membership, assignments, document)
