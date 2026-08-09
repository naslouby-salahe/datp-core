from pathlib import Path

import pytest

from datp_core.core.errors import CapabilityError
from datp_core.core.identifiers import FederatedThresholdMethod, PopulationId, SplitProtocolId
from datp_core.core.numeric import Seed
from datp_core.data.ciciot2023.capabilities import CICIOT2023_CAPABILITIES
from datp_core.data.ciciot2023.populations import construct_ciciot_file_clients
from datp_core.data.populations.contracts import (
    CICIOT_FILE_CLIENTS,
    CapabilityStatus,
    build_population_capabilities,
    population_evidence_role,
)


def test_ciciot_builds_exactly_sixty_three_file_clients(ciciot_canonical_root: Path) -> None:
    construction = construct_ciciot_file_clients(
        ciciot_canonical_root, partition_seed=Seed(1), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    manifest, membership = construction.manifest, construction.membership
    assert len(manifest.document.accepted_clients) == 63
    assert membership.get_column("client_id").n_unique() == 63
    # ineligible row from Merged01 local=8 is excluded
    assert membership.height == 63 * 9 - 1


def test_ciciot_capabilities_declare_no_physical_or_family_interpretation() -> None:
    capabilities = build_population_capabilities(
        CICIOT_FILE_CLIENTS,
        population_evidence_role(PopulationId.CICIOT_FILE_CLIENTS),
        CICIOT2023_CAPABILITIES,
    )
    assert capabilities.physical_client_validity is CapabilityStatus.NOT_APPLICABLE
    assert capabilities.family_taxonomy is CapabilityStatus.UNAVAILABLE
    assert FederatedThresholdMethod.FAMILY_THRESHOLD not in capabilities.valid_threshold_methods


def test_ciciot_rejects_temporal_interpretation(ciciot_canonical_root: Path) -> None:
    seed = Seed(0)
    with pytest.raises(CapabilityError):
        construct_ciciot_file_clients(
            ciciot_canonical_root,
            partition_seed=seed,
            split_protocol=SplitProtocolId.TEMPORAL_HISTORICAL_FUTURE,
        )


def test_ciciot_excluded_rows_preserve_typed_canonical_reasons(ciciot_canonical_root: Path) -> None:
    construction = construct_ciciot_file_clients(
        ciciot_canonical_root, partition_seed=Seed(1), split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS
    )
    evidence = construction.evidence
    assert evidence is not None
    excluded_rows, per_client = evidence.excluded_rows, evidence.client_eligibility

    assert excluded_rows.height == 1
    assert excluded_rows.get_column("nonfinite_feature").to_list() == [True]
    assert excluded_rows.get_column("missing_or_unrecognized_label").to_list() == [False]
    assert per_client.get_column("excluded_row_count").to_list() == [1]
    assert per_client.get_column("nonfinite_feature").to_list() == [1]
