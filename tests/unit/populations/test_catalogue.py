from pathlib import Path

import pytest

from datp_core.domain.enums import PopulationId, SplitProtocolId
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Seed
from datp_core.populations.catalogue import (
    PopulationConstructionRequest,
    PreprocessingHandoffRequest,
    build_preprocessing_handoff,
    construct_population,
    resolve_population,
)
from datp_core.populations.models import iid_condition


def test_catalogue_resolves_all_five_populations() -> None:
    for population in PopulationId:
        binding = resolve_population(population)
        assert binding.declaration.id is population
        assert binding.capabilities.population is population


def test_catalogue_constructs_and_hands_off(nbaiot_canonical_root: Path) -> None:
    construction = construct_population(
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
            construction=construction,
            deployment_fallback_client_ids=frozenset(),
        )
    )
    assert handoff.assignments.height == construction.membership.height
    assert handoff.client_partition_counts
    assert {item.client_id for item in handoff.client_partition_counts} == set(
        construction.manifest.document.candidate_clients
    )
    assert all(not item.deployment_fallback for item in handoff.client_partition_counts)


def test_dirichlet_construction_requires_explicit_condition(nbaiot_canonical_root: Path) -> None:
    with pytest.raises(ScientificContractError):
        construct_population(
            PopulationConstructionRequest(
                PopulationId.NBAIOT_DIRICHLET_CLIENTS,
                nbaiot_canonical_root,
                Seed(0),
                SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
                None,
            )
        )
    construction = construct_population(
        PopulationConstructionRequest(
            PopulationId.NBAIOT_DIRICHLET_CLIENTS,
            nbaiot_canonical_root,
            Seed(0),
            SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
            iid_condition(),
        )
    )
    assert construction.diagnostics is not None
