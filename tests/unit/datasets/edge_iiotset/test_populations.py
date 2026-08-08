from pathlib import Path

import pytest

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, PopulationId, SplitProtocolId
from datp_core.core.numeric import NonNegativeIntegerValue, Seed
from datp_core.data.edge_iiotset.capabilities import EDGE_IIOTSET_CAPABILITIES
from datp_core.data.edge_iiotset.populations import (
    construct_edge_sensor_groups,
    construct_edge_temporal_groups,
)
from datp_core.data.edge_iiotset.schema import EDGE_BENIGN_SENSOR_GROUPS
from datp_core.data.populations.contracts import (
    EDGE_SENSOR_GROUPS,
    CapabilityStatus,
    ChronologicalPartitionDiagnosticsDocument,
    PopulationFeasibilityStatus,
    build_population_capabilities,
    population_evidence_role,
)


def test_edge_static_includes_ten_groups_with_modbus(edge_canonical_root: Path) -> None:
    construction = construct_edge_sensor_groups(
        edge_canonical_root, partition_seed=Seed(0), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    assert manifest.document.accepted_clients == tuple(sorted(EDGE_BENIGN_SENSOR_GROUPS))
    assert "Modbus" in manifest.document.accepted_clients
    assert membership.get_column("client_id").n_unique() == 10
    assert manifest.document.attack_row_count.value == 0


def test_edge_static_capabilities_declare_no_attack_or_family_interpretation() -> None:
    capabilities = build_population_capabilities(
        EDGE_SENSOR_GROUPS,
        population_evidence_role(PopulationId.EDGE_SENSOR_GROUPS),
        EDGE_IIOTSET_CAPABILITIES,
    )
    assert capabilities.client_level_attack_assignment is CapabilityStatus.UNAVAILABLE
    assert capabilities.attack_sensitive_evaluation is CapabilityStatus.UNAVAILABLE
    assert capabilities.family_taxonomy is CapabilityStatus.UNAVAILABLE
    assert FederatedThresholdMethod.FAMILY_THRESHOLD not in capabilities.valid_threshold_methods


def test_temporal_population_excludes_invalid_chronology(edge_canonical_root: Path) -> None:
    construction = construct_edge_temporal_groups(
        edge_canonical_root,
        partition_seed=Seed(0),
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
    )
    manifest, membership, diagnostics = construction.manifest, construction.membership, construction.diagnostics
    matched_reference = construction.matched_reference
    assert isinstance(diagnostics, ChronologicalPartitionDiagnosticsDocument)
    assert matched_reference is not None
    assert manifest.document.feasibility_status is PopulationFeasibilityStatus.INFEASIBLE
    assert diagnostics.observed_eligible_group_count == NonNegativeIntegerValue(0)
    assert "Modbus" not in diagnostics.eligible_group_ids
    assert membership.height == 0
    assert matched_reference.membership.height == 0
    assert matched_reference.manifest.document.split_protocol is SplitProtocolId.RANDOM_FRACTIONAL_STATIC_REFERENCE


def test_temporal_population_accepts_only_verified_groups(edge_temporal_eligible_root: Path) -> None:
    construction = construct_edge_temporal_groups(
        edge_temporal_eligible_root,
        partition_seed=Seed(1),
        split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
    )
    manifest, membership, diagnostics = construction.manifest, construction.membership, construction.diagnostics
    matched_reference = construction.matched_reference
    assert isinstance(diagnostics, ChronologicalPartitionDiagnosticsDocument)
    assert matched_reference is not None
    assert diagnostics.observed_eligible_group_count == NonNegativeIntegerValue(9)
    assert "Modbus" not in manifest.document.accepted_clients
    assert manifest.document.feasibility_status is PopulationFeasibilityStatus.FEASIBLE
    assert membership.get_column("client_id").n_unique() == 9
    assert "capture_timestamp" in membership.columns
    assert matched_reference.membership.get_column("client_id").n_unique() == 9
    assert set(matched_reference.membership.get_column("client_id").unique().to_list()) == set(
        membership.get_column("client_id").unique().to_list()
    )


def test_temporal_rejects_non_temporal_primary_protocol(edge_temporal_eligible_root: Path) -> None:
    with pytest.raises(ScientificContractError):
        construct_edge_temporal_groups(
            edge_temporal_eligible_root,
            partition_seed=Seed(0),
            split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
        )
