from datp_core.domain.enums import CapabilityStatus, EvidenceRole, PopulationId, PopulationIdentityKind
from datp_core.populations.capabilities import population_capabilities, population_declaration


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
