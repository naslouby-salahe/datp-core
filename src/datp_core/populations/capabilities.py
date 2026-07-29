"""Population capability profiles derived from protocol and dataset declarations."""

from datp_core.datasets.capabilities import DatasetCapabilities
from datp_core.datasets.catalogue import dataset_binding
from datp_core.domain.enums import (
    CapabilityStatus,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PopulationIdentityKind,
)
from datp_core.domain.errors import CapabilityError
from datp_core.populations.models import PopulationCapabilities
from datp_core.protocols.models import PopulationDeclaration


def population_declaration(population_id: PopulationId) -> PopulationDeclaration:
    from datp_core.populations.catalogue import resolve_population

    return resolve_population(population_id).declaration


def population_capabilities(population_id: PopulationId) -> PopulationCapabilities:
    from datp_core.populations.catalogue import resolve_population

    return resolve_population(population_id).capabilities


def build_population_capabilities(
    declaration: PopulationDeclaration, evidentiary_role: EvidenceRole
) -> PopulationCapabilities:
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
        fpr_evaluation=_fpr_status(dataset_capabilities),
        attack_sensitive_evaluation=_attack_metric_status(declaration, dataset_capabilities),
        temporal_support=_temporal_status(declaration, dataset_capabilities),
        valid_threshold_methods=_threshold_methods(declaration, dataset_capabilities),
        evidentiary_role=evidentiary_role,
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


def _fpr_status(capabilities: DatasetCapabilities) -> CapabilityStatus:
    return capabilities.metrics.status_for(MetricId.FALSE_POSITIVE_RATE)


def _attack_metric_status(declaration: PopulationDeclaration, capabilities: DatasetCapabilities) -> CapabilityStatus:
    if not declaration.requires_client_attack_assignment:
        return CapabilityStatus.UNAVAILABLE
    if not capabilities.attack_assignment.client_level_assignment_available:
        return CapabilityStatus.UNAVAILABLE
    statuses = frozenset(
        capabilities.metrics.status_for(metric)
        for metric in (
            MetricId.TRUE_POSITIVE_RATE,
            MetricId.BALANCED_ACCURACY,
            MetricId.BINARY_MACRO_F1,
            MetricId.AUROC,
        )
    )
    if statuses == {CapabilityStatus.SUPPORTED}:
        return CapabilityStatus.SUPPORTED
    if CapabilityStatus.CONDITIONAL in statuses:
        return CapabilityStatus.CONDITIONAL
    return CapabilityStatus.UNAVAILABLE


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
