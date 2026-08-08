from pathlib import Path

import pytest

from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import (
    DatasetId,
    EvidenceRole,
    PopulationId,
    PopulationIdentityKind,
    SplitProtocolId,
)
from datp_core.core.numeric import Seed
from datp_core.data.populations.construction import PreprocessingHandoffRequest, build_preprocessing_handoff
from datp_core.data.populations.contracts import CapabilityStatus, PopulationConstructionRequest, iid_condition
from datp_core.data.registry import (
    construct_population,
    dataset_binding,
    population_capabilities,
    population_declaration,
    resolve_population,
)


def test_catalogue_dispatches_every_dataset_id() -> None:
    assert tuple(dataset_binding(dataset_id).schema.dataset for dataset_id in DatasetId) == tuple(DatasetId)


def test_catalogue_rejects_invalid_runtime_identity() -> None:
    try:
        dataset_binding.__call__("invalid")
    except ValueError:
        return
    raise AssertionError("invalid dataset identity was accepted")


def test_registry_resolves_all_five_populations() -> None:
    for population in PopulationId:
        binding = resolve_population(population)
        assert binding.population is population
        assert binding.declaration.id is population
        assert binding.capabilities.population is population


def test_registry_constructs_and_hands_off(nbaiot_canonical_root: Path) -> None:
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
    assert {item.client.client_id for item in handoff.client_partition_counts} == set(
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


def test_population_capabilities_derive_from_protocol_and_dataset() -> None:
    natural = population_capabilities(PopulationId.NBAIOT_NATURAL_DEVICES)
    assert natural.identity_kind is PopulationIdentityKind.PHYSICAL_DEVICES
    assert natural.confirmatory_eligible is True
    assert natural.family_taxonomy is CapabilityStatus.SUPPORTED
    assert natural.client_level_attack_assignment is CapabilityStatus.SUPPORTED
    assert natural.evidentiary_role is EvidenceRole.CONFIRMATORY

    cic = population_capabilities(PopulationId.CICIOT_FILE_CLIENTS)
    assert cic.physical_client_validity is CapabilityStatus.NOT_APPLICABLE
    assert cic.family_taxonomy is CapabilityStatus.UNAVAILABLE
    assert cic.chronology is CapabilityStatus.UNAVAILABLE
    assert cic.client_level_attack_assignment is CapabilityStatus.UNAVAILABLE
    assert cic.evidentiary_role is EvidenceRole.APPLICABILITY_BOUNDARY

    edge = population_capabilities(PopulationId.EDGE_SENSOR_GROUPS)
    assert edge.attack_sensitive_evaluation is CapabilityStatus.UNAVAILABLE
    assert edge.evidentiary_role is EvidenceRole.EXTERNAL_VALIDATION

    temporal = population_capabilities(PopulationId.EDGE_TEMPORAL_GROUPS)
    assert temporal.chronology is CapabilityStatus.CONDITIONAL
    assert temporal.temporal_support is CapabilityStatus.SUPPORTED
    assert temporal.evidentiary_role is EvidenceRole.TEMPORAL_BOUNDARY


def test_declarations_match_locked_client_counts() -> None:
    assert population_declaration(PopulationId.NBAIOT_NATURAL_DEVICES).client_count.value == 9
    assert population_declaration(PopulationId.NBAIOT_DIRICHLET_CLIENTS).client_count.value == 20
    assert population_declaration(PopulationId.CICIOT_FILE_CLIENTS).client_count.value == 63
    assert population_declaration(PopulationId.EDGE_SENSOR_GROUPS).client_count.value == 10
    assert population_declaration(PopulationId.EDGE_TEMPORAL_GROUPS).client_count.value == 9
