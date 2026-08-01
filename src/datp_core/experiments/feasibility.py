"""Capability-first feasibility decisions for external and temporal execution."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TemporalState,
)
from datp_core.populations.capabilities import population_capabilities


class FeasibilityReason(StrEnum):
    FEASIBLE = "feasible"
    INVALID_EXPERIMENT_IDENTITY = "invalid_experiment_identity"
    EXTERNAL_PROMOTED_TO_CONFIRMATORY = "external_promoted_to_confirmatory"
    CONFIRMATORY_ROUTE_PROHIBITED = "confirmatory_route_prohibited"
    ATTACK_SENSITIVE_EDGE_METRIC = "attack_sensitive_edge_metric"
    FAMILY_THRESHOLD_UNAVAILABLE = "family_threshold_unavailable"
    CIC_TEMPORAL_UNAVAILABLE = "ciciot_temporal_unavailable"
    INVALID_TEMPORAL_CHRONOLOGY = "invalid_temporal_chronology"
    MODBUS_TEMPORAL_UNAVAILABLE = "modbus_temporal_unavailable"
    GROUP_ASSIGNMENT_UNAVAILABLE = "group_assignment_unavailable"
    THRESHOLD_METHOD_UNSUPPORTED = "threshold_method_unsupported"
    MATERIALITY_PROTOCOL_UNAVAILABLE = "materiality_protocol_unavailable"
    REQUIRED_ARTIFACT_UNAVAILABLE = "required_artifact_unavailable"
    TEMPORAL_CLIENT_SET_MISMATCH = "temporal_client_set_mismatch"
    FUTURE_LEAKAGE = "future_leakage"
    DIVERGENCE_SEMANTICS_UNRESOLVED = "divergence_semantics_unresolved"
    ATTACK_ASSIGNMENT_MISREPRESENTED = "attack_assignment_misrepresented"


_ATTACK_SENSITIVE_METRICS = frozenset(
    (
        MetricId.TRUE_POSITIVE_RATE,
        MetricId.BALANCED_ACCURACY,
        MetricId.BINARY_MACRO_F1,
        MetricId.AUROC,
        MetricId.TPR_COEFFICIENT_OF_VARIATION,
        MetricId.P10_BINARY_MACRO_F1,
        MetricId.WORST_CLIENT_BALANCED_ACCURACY,
        MetricId.MEAN_CLIENT_MACRO_F1,
        MetricId.POOLED_MACRO_F1,
        MetricId.MEAN_CLIENT_BALANCED_ACCURACY,
    )
)


@dataclass(frozen=True, slots=True)
class ExternalTemporalFeasibilityRequest:
    experiment: ExperimentId
    population: PopulationId
    evidence_role: EvidenceRole
    threshold_method: FederatedThresholdMethod
    requested_metrics: tuple[MetricId, ...]
    routed_through_confirmatory_command: bool
    grouped_assignment_available: bool
    required_artifacts_available: bool
    attack_assignment_claimed_available: bool
    chronology_valid: bool = True
    includes_modbus: bool = False
    materiality_protocol_available: bool = True
    temporal_client_sets_match: bool = True
    future_leakage_detected: bool = False
    divergence_required: bool = False
    divergence_semantics_resolved: bool = True
    temporal_state: TemporalState | None = None
    recovery_ratio_requested: bool = False


@dataclass(frozen=True, slots=True)
class FeasibilityDecision:
    availability: AvailabilityStatus
    reason: FeasibilityReason
    evidence: str

    @property
    def feasible(self) -> bool:
        return self.availability is AvailabilityStatus.AVAILABLE


def assess_external_temporal_feasibility(request: ExternalTemporalFeasibilityRequest) -> FeasibilityDecision:
    """Reject invalid requests before training, scoring, or threshold construction."""
    if request.evidence_role is EvidenceRole.CONFIRMATORY:
        return _infeasible(
            FeasibilityReason.EXTERNAL_PROMOTED_TO_CONFIRMATORY,
            "external and temporal evidence cannot become confirmatory",
        )
    identity = _validate_identity(request)
    if identity is not None:
        return identity
    if request.routed_through_confirmatory_command:
        return _infeasible(
            FeasibilityReason.CONFIRMATORY_ROUTE_PROHIBITED, "external and temporal execution have separate identities"
        )
    if request.population is PopulationId.EDGE_SENSOR_GROUPS:
        return _edge_static_decision(request)
    if request.population is PopulationId.CICIOT_FILE_CLIENTS:
        return _ciciot_decision(request)
    if request.population is PopulationId.EDGE_TEMPORAL_GROUPS:
        return _temporal_decision(request)
    return _infeasible(
        FeasibilityReason.INVALID_EXPERIMENT_IDENTITY,
        "Phase 11 permits only Edge static, CIC file-client, and Edge temporal populations",
    )


def _validate_identity(request: ExternalTemporalFeasibilityRequest) -> FeasibilityDecision | None:
    match request.population, request.experiment, request.evidence_role:
        case (
            PopulationId.EDGE_SENSOR_GROUPS,
            ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION,
            EvidenceRole.EXTERNAL_VALIDATION,
        ):
            return None
        case (
            PopulationId.CICIOT_FILE_CLIENTS,
            ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY,
            EvidenceRole.APPLICABILITY_BOUNDARY,
        ):
            return None
        case (
            PopulationId.EDGE_TEMPORAL_GROUPS,
            ExperimentId.EDGE_ONE_SHOT_RECALIBRATION,
            EvidenceRole.TEMPORAL_BOUNDARY,
        ):
            return None
        case _:
            return _infeasible(
                FeasibilityReason.INVALID_EXPERIMENT_IDENTITY,
                "experiment, population, and evidence role must be the declared Phase 11 tuple",
            )


def _edge_static_decision(request: ExternalTemporalFeasibilityRequest) -> FeasibilityDecision:
    if request.temporal_state is not None:
        return _infeasible(
            FeasibilityReason.INVALID_EXPERIMENT_IDENTITY, "static external validation has no temporal deployment state"
        )
    if request.attack_assignment_claimed_available:
        return _infeasible(
            FeasibilityReason.ATTACK_ASSIGNMENT_MISREPRESENTED, "Edge attack rows are not assigned to sensor groups"
        )
    if any(metric in _ATTACK_SENSITIVE_METRICS for metric in request.requested_metrics):
        return _infeasible(
            FeasibilityReason.ATTACK_SENSITIVE_EDGE_METRIC,
            "Edge supports external benign operating-point outcomes only",
        )
    return _threshold_and_artifact_decision(request)


def _ciciot_decision(request: ExternalTemporalFeasibilityRequest) -> FeasibilityDecision:
    if request.temporal_state is not None:
        return _infeasible(
            FeasibilityReason.CIC_TEMPORAL_UNAVAILABLE, "CIC file-defined pseudo-clients have no verified chronology"
        )
    if request.attack_assignment_claimed_available:
        return _infeasible(
            FeasibilityReason.ATTACK_ASSIGNMENT_MISREPRESENTED,
            "CIC file identity is not physical-client attack assignment",
        )
    if request.divergence_required and not request.divergence_semantics_resolved:
        return _blocked(
            FeasibilityReason.DIVERGENCE_SEMANTICS_UNRESOLVED, "the declared divergence construction remains unresolved"
        )
    return _threshold_and_artifact_decision(request)


def _temporal_decision(request: ExternalTemporalFeasibilityRequest) -> FeasibilityDecision:
    if request.temporal_state is None:
        return _infeasible(
            FeasibilityReason.INVALID_EXPERIMENT_IDENTITY, "temporal execution requires a declared deployment state"
        )
    if not request.chronology_valid:
        return _infeasible(
            FeasibilityReason.INVALID_TEMPORAL_CHRONOLOGY, "only complete PCAP-backed chronology is admissible"
        )
    if request.includes_modbus:
        return _infeasible(
            FeasibilityReason.MODBUS_TEMPORAL_UNAVAILABLE,
            "Modbus frame.time values are address literals, not chronology",
        )
    if request.attack_assignment_claimed_available:
        return _infeasible(
            FeasibilityReason.ATTACK_ASSIGNMENT_MISREPRESENTED, "Edge temporal groups have benign rows only"
        )
    if any(metric in _ATTACK_SENSITIVE_METRICS for metric in request.requested_metrics):
        return _infeasible(
            FeasibilityReason.ATTACK_SENSITIVE_EDGE_METRIC,
            "Edge temporal evidence supports benign operating-point outcomes only",
        )
    if request.recovery_ratio_requested and not request.materiality_protocol_available:
        return _blocked(
            FeasibilityReason.MATERIALITY_PROTOCOL_UNAVAILABLE,
            "recovery-ratio interpretation requires the declared materiality protocol",
        )
    if not request.temporal_client_sets_match:
        return _infeasible(
            FeasibilityReason.TEMPORAL_CLIENT_SET_MISMATCH,
            "all temporal states require identical eligible client identities",
        )
    if request.future_leakage_detected:
        return _infeasible(
            FeasibilityReason.FUTURE_LEAKAGE, "future rows cannot affect historical fitting or frozen thresholds"
        )
    return _threshold_and_artifact_decision(request)


def _threshold_and_artifact_decision(request: ExternalTemporalFeasibilityRequest) -> FeasibilityDecision:
    if request.threshold_method is FederatedThresholdMethod.FAMILY_THRESHOLD:
        return _infeasible(
            FeasibilityReason.FAMILY_THRESHOLD_UNAVAILABLE, "Phase 11 populations have no audited family taxonomy"
        )
    if (
        request.threshold_method is FederatedThresholdMethod.CLUSTER_THRESHOLD
        and not request.grouped_assignment_available
    ):
        return _infeasible(
            FeasibilityReason.GROUP_ASSIGNMENT_UNAVAILABLE,
            "grouped thresholds require a completed Phase 09 assignment artifact",
        )
    capabilities = population_capabilities(request.population)
    if request.threshold_method not in capabilities.valid_threshold_methods:
        return _infeasible(
            FeasibilityReason.THRESHOLD_METHOD_UNSUPPORTED,
            "population capability contract does not authorize this threshold method",
        )
    if not request.required_artifacts_available:
        return _blocked(
            FeasibilityReason.REQUIRED_ARTIFACT_UNAVAILABLE,
            "model, score, threshold, and evaluation provenance must be complete",
        )
    return FeasibilityDecision(
        AvailabilityStatus.AVAILABLE,
        FeasibilityReason.FEASIBLE,
        "declared identity and capability requirements are satisfied",
    )


def _infeasible(reason: FeasibilityReason, evidence: str) -> FeasibilityDecision:
    return FeasibilityDecision(AvailabilityStatus.INFEASIBLE, reason, evidence)


def _blocked(reason: FeasibilityReason, evidence: str) -> FeasibilityDecision:
    return FeasibilityDecision(AvailabilityStatus.UNAVAILABLE, reason, evidence)
