from pathlib import Path

import polars as pl
import pytest

from datp_core.domain.enums import DatasetId, PartitionRole, PopulationId, SplitProtocolId
from datp_core.domain.errors import DataIntegrityError, LeakageError
from datp_core.domain.values import Checksum, Seed
from datp_core.populations.integrity import validate_population_manifest, validate_split_manifest
from datp_core.populations.models import SplitConstructionRequest, SplitManifestDocument
from datp_core.populations.nbaiot_natural_devices import build_nbaiot_natural_devices
from datp_core.populations.splits import split_membership


def test_integrity_accepts_valid_population_and_split(nbaiot_canonical_root: Path) -> None:
    manifest, membership = build_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    validate_population_manifest(manifest, membership)
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
    validate_split_manifest(membership, assignments, split_manifest)


def test_integrity_detects_duplicate_split_assignment(nbaiot_canonical_root: Path) -> None:
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
    poisoned = pl.concat([assignments, assignments.head(1)])
    with pytest.raises(DataIntegrityError):
        validate_split_manifest(membership, poisoned, split_manifest)


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
        assignment_row_count=2,
        train_row_count=0,
        calibration_row_count=2,
        evaluation_row_count=0,
        future_recalibration_row_count=0,
        static_reference_reserve_row_count=0,
        assignment_checksum=Checksum("b" * 64),
        population_manifest_checksum=Checksum("c" * 64),
    )
    with pytest.raises(LeakageError):
        validate_split_manifest(membership, assignments, document)
