from pathlib import Path

import polars as pl

from datp_core.domain.enums import ControlledPartitionKind, SplitProtocolId
from datp_core.domain.values import DirichletConcentration, Seed
from datp_core.populations.models import dirichlet_condition, iid_condition
from datp_core.populations.nbaiot_dirichlet_clients import build_nbaiot_dirichlet_clients


def test_dirichlet_constructs_twenty_clients_and_conserves_rows(nbaiot_canonical_root: Path) -> None:
    manifest, membership, diagnostics = build_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(2),
        condition=dirichlet_condition(DirichletConcentration(0.5)),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    )
    assert len(manifest.document.accepted_clients) == 20
    assert membership.height == 9 * (30 + 12)
    assert membership.get_column("stable_row_id").n_unique() == membership.height
    assert diagnostics.partition_kind is ControlledPartitionKind.DIRICHLET
    assert sum(diagnostics.client_row_counts) == membership.height


def test_iid_is_separate_typed_condition_and_is_deterministic(nbaiot_canonical_root: Path) -> None:
    first, first_membership, first_diag = build_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(4),
        condition=iid_condition(),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    )
    second, second_membership, second_diag = build_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(4),
        condition=iid_condition(),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    )
    assert first_diag.partition_kind is ControlledPartitionKind.IID
    assert first_diag.concentration is None
    assert first_membership.equals(second_membership)
    assert first.document.membership_checksum == second.document.membership_checksum
    assert first_diag.client_row_counts == second_diag.client_row_counts


def test_dirichlet_does_not_drop_or_duplicate_rows(nbaiot_canonical_root: Path) -> None:
    _, membership, _ = build_nbaiot_dirichlet_clients(
        nbaiot_canonical_root,
        partition_seed=Seed(7),
        condition=dirichlet_condition(DirichletConcentration(0.1)),
        split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    )
    counts = membership.group_by("stable_row_id").len()
    assert counts.filter(pl.col("len") != 1).height == 0
