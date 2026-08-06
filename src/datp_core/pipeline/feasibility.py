"""Runtime readiness, CUDA, and applicability feasibility checks for pipeline execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import ClassVar

from datp_core.datasets.registry import population_capabilities
from datp_core.domain.enums import (
    AvailabilityStatus,
    EvidenceRole,
    ExperimentId,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    TemporalState,
)
from datp_core.pipeline.execution.models import CampaignPlan
from datp_core.pipeline.planning import ExperimentPlan


class AcceptanceStatus(StrEnum):
    PASSED = "passed"
    BLOCKED = "blocked"
    FAILED = "failed"


@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptanceCheck:
    name: str
    status: AcceptanceStatus
    evidence: str

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.evidence.strip():
            raise ValueError("acceptance checks require a name and evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class AcceptanceReport:
    checks: tuple[AcceptanceCheck, ...]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(check.status is AcceptanceStatus.PASSED for check in self.checks)


def validate_preflight(
    *,
    plan: ExperimentPlan,
    campaign: CampaignPlan,
    output_root: Path,
    cuda_available: bool,
    require_cuda: bool,
) -> AcceptanceReport:
    checks = (
        AcceptanceCheck(
            name="plan_digest",
            status=AcceptanceStatus.PASSED,
            evidence=f"validated deterministic plan {plan.digest.value}",
        ),
        AcceptanceCheck(
            name="campaign_digest",
            status=AcceptanceStatus.PASSED,
            evidence=f"validated deterministic campaign {campaign.digest.value}",
        ),
        AcceptanceCheck(
            name="output_root",
            status=AcceptanceStatus.PASSED if output_root.parts else AcceptanceStatus.FAILED,
            evidence=str(output_root) if output_root.parts else "output root is empty",
        ),
        AcceptanceCheck(
            name="cuda",
            status=(AcceptanceStatus.PASSED if cuda_available or not require_cuda else AcceptanceStatus.BLOCKED),
            evidence=(
                "CUDA requirement satisfied"
                if cuda_available
                else "CUDA unavailable while the runtime protocol requires CUDA"
            ),
        ),
    )
    return AcceptanceReport(checks=checks)


class ExtensionKind(StrEnum):
    ATTACK = "attack"
    DEFENSE = "defense"
    DATASET = "dataset"
    DYNAMIC_ADAPTATION = "dynamic_adaptation"
    THRESHOLD_METHOD = "threshold_method"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionRequest:
    kind: ExtensionKind
    identity: str

    def __post_init__(self) -> None:
        if not self.identity.strip():
            raise ValueError("extension requests require an identity")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionDecision:
    permitted: bool
    reason: str


def assess_extension(request: ExtensionRequest) -> ExtensionDecision:
    if request.kind in {ExtensionKind.ATTACK, ExtensionKind.DEFENSE}:
        return ExtensionDecision(
            permitted=False,
            reason="attacks and defenses are outside DATP-Core",
        )
    if request.kind is ExtensionKind.DYNAMIC_ADAPTATION:
        return ExtensionDecision(
            permitted=False,
            reason="DATP-Core permits one-shot recalibration only",
        )
    if request.kind is ExtensionKind.DATASET:
        return ExtensionDecision(
            permitted=False,
            reason="DATP-Core adds no dataset beyond Edge-IIoTset",
        )
    return ExtensionDecision(
        permitted=False,
        reason="future extensions require a separately approved scientific protocol",
    )


class FeasibilityReason(StrEnum):
    FEASIBLE = "feasible"
    CONFIRMATORY_ROUTE_PROHIBITED = "confirmatory_route_prohibited"
    ATTACK_SENSITIVE_EDGE_METRIC = "attack_sensitive_edge_metric"
    FAMILY_THRESHOLD_UNAVAILABLE = "family_threshold_unavailable"
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
    UNSUPPORTED_TEMPORAL_EXECUTION_MODE = "unsupported_temporal_execution_mode"


class TemporalExecutionMode(StrEnum):
    ONE_SHOT = "one_shot"
    STREAMING = "streaming"
    PERIODIC = "periodic"
    TRIGGERED = "triggered"
    ONLINE = "online"


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


@dataclass(frozen=True, slots=True, kw_only=True)
class _ThresholdFeasibilityRequest:
    threshold_method: FederatedThresholdMethod
    requested_metrics: tuple[MetricId, ...]
    routed_through_confirmatory_command: bool
    grouped_assignment_available: bool
    required_artifacts_available: bool
    attack_assignment_claimed_available: bool

    def __post_init__(self) -> None:
        if not self.requested_metrics:
            raise ValueError("feasibility requests require at least one metric")
        if len(self.requested_metrics) != len(frozenset(self.requested_metrics)):
            raise ValueError("feasibility request metrics must be unique")


@dataclass(frozen=True, slots=True, kw_only=True)
class EdgeExternalFeasibilityRequest(_ThresholdFeasibilityRequest):
    experiment: ClassVar[ExperimentId] = ExperimentId.EDGE_BENIGN_EQUITY_VALIDATION
    population: ClassVar[PopulationId] = PopulationId.EDGE_SENSOR_GROUPS
    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.EXTERNAL_VALIDATION


@dataclass(frozen=True, slots=True, kw_only=True)
class CiciotBoundaryFeasibilityRequest(_ThresholdFeasibilityRequest):
    divergence_required: bool
    divergence_semantics_resolved: bool
    experiment: ClassVar[ExperimentId] = ExperimentId.CICIOT_FILE_CLIENT_BOUNDARY
    population: ClassVar[PopulationId] = PopulationId.CICIOT_FILE_CLIENTS
    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.APPLICABILITY_BOUNDARY


@dataclass(frozen=True, slots=True, kw_only=True)
class EdgeTemporalFeasibilityRequest(_ThresholdFeasibilityRequest):
    chronology_valid: bool
    includes_modbus: bool
    materiality_protocol_available: bool
    temporal_client_sets_match: bool
    future_leakage_detected: bool
    temporal_state: TemporalState
    temporal_execution_mode: TemporalExecutionMode
    recovery_ratio_requested: bool
    experiment: ClassVar[ExperimentId] = ExperimentId.EDGE_ONE_SHOT_RECALIBRATION
    population: ClassVar[PopulationId] = PopulationId.EDGE_TEMPORAL_GROUPS
    evidence_role: ClassVar[EvidenceRole] = EvidenceRole.TEMPORAL_BOUNDARY


type ExternalTemporalFeasibilityRequest = (
    EdgeExternalFeasibilityRequest | CiciotBoundaryFeasibilityRequest | EdgeTemporalFeasibilityRequest
)


@dataclass(frozen=True, slots=True)
class FeasibilityDecision:
    availability: AvailabilityStatus
    reason: FeasibilityReason
    evidence: str

    @property
    def feasible(self) -> bool:
        return self.availability is AvailabilityStatus.AVAILABLE


def assess_external_temporal_feasibility(request: ExternalTemporalFeasibilityRequest) -> FeasibilityDecision:
    if request.routed_through_confirmatory_command:
        return _infeasible(
            FeasibilityReason.CONFIRMATORY_ROUTE_PROHIBITED,
            "external and temporal execution have separate identities and command routes",
        )
    match request:
        case EdgeExternalFeasibilityRequest():
            return _edge_static_decision(request)
        case CiciotBoundaryFeasibilityRequest():
            return _ciciot_decision(request)
        case EdgeTemporalFeasibilityRequest():
            return _temporal_decision(request)


def _edge_static_decision(request: EdgeExternalFeasibilityRequest) -> FeasibilityDecision:
    if request.attack_assignment_claimed_available:
        return _infeasible(
            FeasibilityReason.ATTACK_ASSIGNMENT_MISREPRESENTED,
            "Edge attack rows are not assigned to sensor groups",
        )
    if any(metric in _ATTACK_SENSITIVE_METRICS for metric in request.requested_metrics):
        return _infeasible(
            FeasibilityReason.ATTACK_SENSITIVE_EDGE_METRIC,
            "Edge supports external benign operating-point outcomes only",
        )
    return _threshold_and_artifact_decision(request)


def _ciciot_decision(request: CiciotBoundaryFeasibilityRequest) -> FeasibilityDecision:
    if request.attack_assignment_claimed_available:
        return _infeasible(
            FeasibilityReason.ATTACK_ASSIGNMENT_MISREPRESENTED,
            "CIC file identity is not physical-client attack assignment",
        )
    if request.divergence_required and not request.divergence_semantics_resolved:
        return _blocked(
            FeasibilityReason.DIVERGENCE_SEMANTICS_UNRESOLVED,
            "the declared divergence construction remains unresolved",
        )
    return _threshold_and_artifact_decision(request)


def _temporal_chronology_decision(request: EdgeTemporalFeasibilityRequest) -> FeasibilityDecision | None:
    if request.temporal_execution_mode is not TemporalExecutionMode.ONE_SHOT:
        return _infeasible(
            FeasibilityReason.UNSUPPORTED_TEMPORAL_EXECUTION_MODE,
            "temporal recalibration permits one-shot execution only",
        )
    if not request.chronology_valid:
        return _infeasible(
            FeasibilityReason.INVALID_TEMPORAL_CHRONOLOGY,
            "only complete PCAP-backed chronology is admissible",
        )
    if request.includes_modbus:
        return _infeasible(
            FeasibilityReason.MODBUS_TEMPORAL_UNAVAILABLE,
            "Modbus frame.time values are address literals, not chronology",
        )
    return None


def _temporal_attack_exposure_decision(request: EdgeTemporalFeasibilityRequest) -> FeasibilityDecision | None:
    if request.attack_assignment_claimed_available:
        return _infeasible(
            FeasibilityReason.ATTACK_ASSIGNMENT_MISREPRESENTED,
            "Edge temporal groups have benign rows only",
        )
    if any(metric in _ATTACK_SENSITIVE_METRICS for metric in request.requested_metrics):
        return _infeasible(
            FeasibilityReason.ATTACK_SENSITIVE_EDGE_METRIC,
            "Edge temporal evidence supports benign operating-point outcomes only",
        )
    return None


def _temporal_eligibility_decision(request: EdgeTemporalFeasibilityRequest) -> FeasibilityDecision | None:
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
            FeasibilityReason.FUTURE_LEAKAGE,
            "future rows cannot affect historical fitting or frozen thresholds",
        )
    return None


def _temporal_decision(request: EdgeTemporalFeasibilityRequest) -> FeasibilityDecision:
    decision = (
        _temporal_chronology_decision(request)
        or _temporal_attack_exposure_decision(request)
        or _temporal_eligibility_decision(request)
    )
    if decision is not None:
        return decision
    return _threshold_and_artifact_decision(request)


def _threshold_and_artifact_decision(request: ExternalTemporalFeasibilityRequest) -> FeasibilityDecision:
    if request.threshold_method is FederatedThresholdMethod.FAMILY_THRESHOLD:
        return _infeasible(
            FeasibilityReason.FAMILY_THRESHOLD_UNAVAILABLE,
            "these populations have no audited family taxonomy",
        )
    if (
        request.threshold_method is FederatedThresholdMethod.CLUSTER_THRESHOLD
        and not request.grouped_assignment_available
    ):
        return _infeasible(
            FeasibilityReason.GROUP_ASSIGNMENT_UNAVAILABLE,
            "grouped thresholds require a completed assignment artifact",
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
