"""Population capability profiles derived from protocol and dataset declarations."""

from datp_core.datasets.capabilities import DatasetCapabilities
from datp_core.datasets.catalogue import dataset_binding
from datp_core.domain.enums import (
    CapabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    PopulationId,
    PopulationIdentityKind,
)
from datp_core.domain.errors import CapabilityError
from datp_core.populations.models import PopulationCapabilities
from datp_core.protocols.models import PopulationDeclaration
from datp_core.protocols.populations import POPULATIONS


def population_declaration(population_id: PopulationId) -> PopulationDeclaration:
    for declaration in POPULATIONS:
        if declaration.id is population_id:
            return declaration
    raise CapabilityError(
        "unknown population identity",
        subject=population_id,
        reason="population is absent from the locked protocol catalogue",
    )


def population_capabilities(population_id: PopulationId) -> PopulationCapabilities:
    declaration = population_declaration(population_id)
    dataset_capabilities = dataset_binding(declaration.dataset).capabilities
    _require_population_allowed(declaration, dataset_capabilities)
    return PopulationCapabilities(
        population=declaration.id,
        dataset=declaration.dataset,
        identity_kind=declaration.identity_kind,
        declared_client_count=declaration.client_count,
        physical_client_validity=_physical_validity(declaration, dataset_capabilities),
        family_taxonomy=_family_status(declaration, dataset_capabilities),
        chronology=_chronology_status(declaration, dataset_capabilities),
        client_level_attack_assignment=_attack_status(declaration, dataset_capabilities),
        fpr_evaluation=_fpr_status(declaration, dataset_capabilities),
        attack_sensitive_evaluation=_attack_metric_status(declaration, dataset_capabilities),
        temporal_support=_temporal_status(declaration, dataset_capabilities),
        valid_threshold_methods=_threshold_methods(declaration, dataset_capabilities),
        evidentiary_role=_evidentiary_role(declaration.identity_kind),
        confirmatory_eligible=declaration.is_confirmatory_population,
    )


def _require_population_allowed(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> None:
    if declaration.id not in capabilities.valid_populations:
        raise CapabilityError(
            "population is not valid for its dataset",
            subject=declaration.id,
            reason="dataset capability catalogue does not list the population",
        )


def _physical_validity(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    match declaration.identity_kind:
        case PopulationIdentityKind.PHYSICAL_DEVICES:
            return capabilities.physical_clients.status
        case PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS:
            return CapabilityStatus.NOT_APPLICABLE
        case PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS:
            return capabilities.physical_clients.status
        case PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS:
            return CapabilityStatus.NOT_APPLICABLE
        case PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS:
            return capabilities.physical_clients.status


def _family_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_family_taxonomy:
        return CapabilityStatus.UNAVAILABLE
    return capabilities.family_taxonomy.status


def _chronology_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_verified_chronology:
        return CapabilityStatus.UNAVAILABLE
    return capabilities.chronology.status


def _attack_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_client_attack_assignment:
        return CapabilityStatus.UNAVAILABLE
    if not capabilities.attack_assignment.client_level_assignment_available:
        return CapabilityStatus.UNAVAILABLE
    return capabilities.attack_assignment.status


def _fpr_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if declaration.identity_kind is PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS:
        return CapabilityStatus.CONDITIONAL
    return capabilities.metrics.status


def _attack_metric_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_client_attack_assignment:
        return CapabilityStatus.UNAVAILABLE
    if not capabilities.attack_assignment.client_level_assignment_available:
        return CapabilityStatus.UNAVAILABLE
    return CapabilityStatus.SUPPORTED


def _temporal_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_verified_chronology:
        return CapabilityStatus.UNAVAILABLE
    return capabilities.temporal.status


def _threshold_methods(
    declaration: PopulationDeclaration, capabilities: DatasetCapabilities
) -> tuple[FederatedThresholdMethod, ...]:
    supported = tuple(
        item.method
        for item in capabilities.threshold_methods
        if item.status in {CapabilityStatus.SUPPORTED, CapabilityStatus.CONDITIONAL}
    )
    if declaration.requires_family_taxonomy and FederatedThresholdMethod.FAMILY_THRESHOLD not in supported:
        if capabilities.family_taxonomy.status is CapabilityStatus.SUPPORTED:
            return supported + (FederatedThresholdMethod.FAMILY_THRESHOLD,)
    if not declaration.requires_family_taxonomy:
        return tuple(method for method in supported if method is not FederatedThresholdMethod.FAMILY_THRESHOLD)
    return supported


def _evidentiary_role(identity_kind: PopulationIdentityKind) -> EvidenceRole:
    match identity_kind:
        case PopulationIdentityKind.PHYSICAL_DEVICES:
            return EvidenceRole.CONFIRMATORY
        case PopulationIdentityKind.SYNTHETIC_DIRICHLET_CLIENTS:
            return EvidenceRole.MECHANISM
        case PopulationIdentityKind.FILE_DEFINED_PSEUDO_CLIENTS:
            return EvidenceRole.APPLICABILITY_BOUNDARY
        case PopulationIdentityKind.SOURCE_DEFINED_SENSOR_GROUPS:
            return EvidenceRole.EXTERNAL_VALIDATION
        case PopulationIdentityKind.VERIFIED_TEMPORAL_GROUPS:
            return EvidenceRole.TEMPORAL_BOUNDARY
