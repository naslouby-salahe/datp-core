from pathlib import Path

import polars as pl

from datp_core.datasets.nbaiot.populations import construct_nbaiot_dirichlet_clients, construct_nbaiot_natural_devices
from datp_core.datasets.nbaiot.schema import NBAIOT_DEVICE_IDENTITIES
from datp_core.datasets.partitioning.contracts import (
    DirichletPartitionDiagnosticsDocument,
    dirichlet_condition,
    iid_condition,
)
from datp_core.domain.enums import ControlledPartitionKind, PopulationId, SplitProtocolId
from datp_core.domain.values import DirichletConcentration, Seed
from datp_core.protocols.calibration import MINIMUM_BENIGN_SUPPORT


def test_natural_devices_are_exactly_the_audited_nine(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    assert manifest.document.population is PopulationId.NBAIOT_NATURAL_DEVICES
    assert manifest.document.accepted_clients == tuple(sorted(NBAIOT_DEVICE_IDENTITIES))
    assert len(manifest.document.accepted_clients) == 9
    assert membership.get_column("client_id").n_unique() == 9
    assert set(manifest.family_by_client)
    assert manifest.document.benign_row_count == 9 * 30
    assert manifest.document.attack_row_count == 9 * 12
    assert membership.height == manifest.document.total_membership_rows
    assert construction.diagnostics is None


def test_natural_devices_replay_is_deterministic(nbaiot_canonical_root: Path) -> None:
    first = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(3), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    second = construct_nbaiot_natural_devices(
        nbaiot_canonical_root, partition_seed=Seed(3), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    assert first.manifest.document == second.manifest.document
    assert first.membership.equals(second.membership)


def test_dirichlet_constructs_twenty_clients_and_conserves_rows(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(2),
        condition=dirichlet_condition(DirichletConcentration(0.5)),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        minimum_benign_support=MINIMUM_BENIGN_SUPPORT,
    )
    manifest, membership, diagnostics = construction.manifest, construction.membership, construction.diagnostics
    assert isinstance(diagnostics, DirichletPartitionDiagnosticsDocument)
    assert len(manifest.document.accepted_clients) == 20
    assert membership.height == 9 * (30 + 12)
    assert membership.get_column("stable_row_id").n_unique() == membership.height
    assert diagnostics.partition_kind is ControlledPartitionKind.DIRICHLET
    assert sum(diagnostics.client_row_counts) == membership.height


def test_iid_is_separate_typed_condition_and_is_deterministic(nbaiot_canonical_root: Path) -> None:
    first = construct_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(4),
        condition=iid_condition(),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        minimum_benign_support=MINIMUM_BENIGN_SUPPORT,
    )
    second = construct_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(4),
        condition=iid_condition(),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        minimum_benign_support=MINIMUM_BENIGN_SUPPORT,
    )
    assert isinstance(first.diagnostics, DirichletPartitionDiagnosticsDocument)
    assert isinstance(second.diagnostics, DirichletPartitionDiagnosticsDocument)
    assert first.diagnostics.partition_kind is ControlledPartitionKind.IID
    assert first.diagnostics.concentration is None
    assert first.membership.equals(second.membership)
    assert first.manifest.document.membership_checksum == second.manifest.document.membership_checksum
    assert first.diagnostics.client_row_counts == second.diagnostics.client_row_counts


def test_dirichlet_does_not_drop_or_duplicate_rows(nbaiot_canonical_root: Path) -> None:
    construction = construct_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(7),
        condition=dirichlet_condition(DirichletConcentration(0.1)),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        minimum_benign_support=MINIMUM_BENIGN_SUPPORT,
    )
    counts = construction.membership.group_by("stable_row_id").len()
    assert counts.filter(pl.col("len") != 1).height == 0
