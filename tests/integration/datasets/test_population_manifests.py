from pathlib import Path

import pytest

from datp_core.artifacts.provenance import checksum_text
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import PopulationId, SplitProtocolId
from datp_core.core.numeric import Seed
from datp_core.data.populations.construction import PreprocessingHandoffRequest, build_preprocessing_handoff
from datp_core.data.populations.contracts import PopulationConstructionRequest, SplitConstructionRequest, iid_condition
from datp_core.data.populations.splits import split_membership
from datp_core.data.registry import construct_population


def test_end_to_end_manifest_handoff_for_natural_and_dirichlet(nbaiot_canonical_root: Path) -> None:
    natural = construct_population(
        PopulationConstructionRequest(
            PopulationId.NBAIOT_NATURAL_DEVICES,
            nbaiot_canonical_root,
            Seed(0),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            None,
        )
    )
    handoff = build_preprocessing_handoff(
        PreprocessingHandoffRequest(
            construction=natural,
            deployment_fallback_client_ids=frozenset(),
        )
    )
    assert handoff.population_manifest.document.accepted_clients == natural.manifest.document.accepted_clients
    assert handoff.assignments.height == natural.membership.height

    controlled = construct_population(
        PopulationConstructionRequest(
            PopulationId.NBAIOT_DIRICHLET_CLIENTS,
            nbaiot_canonical_root,
            Seed(1),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            iid_condition(),
        )
    )
    assert len(controlled.manifest.document.accepted_clients) == 20


def test_preprocessing_handoff_requires_declared_split_checksum(nbaiot_canonical_root: Path) -> None:
    construction = construct_population(
        PopulationConstructionRequest(
            PopulationId.NBAIOT_NATURAL_DEVICES,
            nbaiot_canonical_root,
            Seed(0),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            None,
        )
    )
    document = construction.manifest.document
    _, split_manifest = split_membership(
        SplitConstructionRequest(
            construction.membership,
            document.population,
            document.dataset,
            document.partition_seed,
            document.split_protocol,
            document.membership_checksum,
        )
    )
    handoff = build_preprocessing_handoff(
        PreprocessingHandoffRequest(
            construction=construction,
            deployment_fallback_client_ids=frozenset(),
            expected_split_manifest_checksum=split_manifest.assignment_checksum,
        )
    )
    assert handoff.assignments.height == construction.membership.height

    with pytest.raises(ScientificContractError, match="does not match the declared split checksum"):
        build_preprocessing_handoff(
            PreprocessingHandoffRequest(
                construction=construction,
                deployment_fallback_client_ids=frozenset(),
                expected_split_manifest_checksum=checksum_text("not the declared split"),
            )
        )


def test_edge_static_manifest(edge_canonical_root: Path) -> None:
    construction = construct_population(
        PopulationConstructionRequest(
            PopulationId.EDGE_SENSOR_GROUPS,
            edge_canonical_root,
            Seed(0),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            None,
        )
    )
    assert len(construction.manifest.document.accepted_clients) == 10
