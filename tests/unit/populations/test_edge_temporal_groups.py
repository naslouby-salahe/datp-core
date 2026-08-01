from pathlib import Path

import pytest

from datp_core.domain.enums import SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Seed
from datp_core.populations.edge_temporal_groups import build_edge_temporal_groups
from datp_core.populations.models import PopulationFeasibilityStatus


def test_temporal_population_excludes_invalid_chronology(edge_canonical_root: Path) -> None:
    manifest, membership, diagnostics, static_manifest, static_membership = build_edge_temporal_groups(
        edge_canonical_root,
        partition_seed=Seed(0),
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
    )
    assert manifest.document.feasibility_status is PopulationFeasibilityStatus.INFEASIBLE
    assert diagnostics.document.observed_eligible_group_count == 0
    assert "Modbus" not in diagnostics.document.eligible_group_ids
    assert membership.height == 0
    assert static_membership.height == 0
    assert static_manifest.document.split_protocol is SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE


def test_temporal_population_accepts_only_verified_groups(edge_temporal_eligible_root: Path) -> None:
    manifest, membership, diagnostics, static_manifest, static_membership = build_edge_temporal_groups(
        edge_temporal_eligible_root,
        partition_seed=Seed(1),
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
    )
    assert diagnostics.document.observed_eligible_group_count == 9
    assert "Modbus" not in manifest.document.accepted_clients
    assert manifest.document.feasibility_status is PopulationFeasibilityStatus.FEASIBLE
    assert membership.get_column("client_id").n_unique() == 9
    assert "capture_timestamp" in membership.columns
    assert static_membership.get_column("client_id").n_unique() == 9
    assert set(static_membership.get_column("client_id").unique().to_list()) == set(
        membership.get_column("client_id").unique().to_list()
    )


def test_temporal_rejects_non_temporal_primary_protocol(edge_temporal_eligible_root: Path) -> None:
    with pytest.raises(ScientificContractError):
        build_edge_temporal_groups(
            edge_temporal_eligible_root,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        )
