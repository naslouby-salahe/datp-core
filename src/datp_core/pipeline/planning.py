"""Deterministic experiment planning and capability-first feasibility."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import blake2b
from typing import ClassVar

from datp_core.domain.enums import (
    AvailabilityStatus,
    DatasetId,
    EvidenceRole,
    ExperimentId,
    ExperimentReadiness,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PreprocessingProtocolId,
    SplitProtocolId,
    TemporalState,
    TrainingModelId,
)
from datp_core.domain.values import ModelCoefficientValue, Seed
from datp_core.populations.capabilities import population_capabilities, population_declaration
from datp_core.preprocessing.models import SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD
from datp_core.protocols.experiments import EXECUTION_IDENTITY_DECLARATIONS, EXPERIMENTS
from datp_core.protocols.models import ExperimentDeclaration, SeedCohort
from datp_core.protocols.populations import split_protocol_for_population
from datp_core.protocols.seeds import CONFIRMATORY_SEED_COHORT
from datp_core.protocols.training import DITTO_TRAINING_PROTOCOLS, FEDPROX_TRAINING_PROTOCOLS

_MODEL_COEFFICIENT_TRAINING_MODELS = frozenset(
    (TrainingModelId.FEDPROX_AUTOENCODER, TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER)
)


def _declared_model_coefficients(training_model: TrainingModelId) -> tuple[ModelCoefficientValue | None, ...]:
    match training_model:
        case TrainingModelId.FEDPROX_AUTOENCODER:
            return tuple(ModelCoefficientValue(protocol.coefficient.value) for protocol in FEDPROX_TRAINING_PROTOCOLS)
        case TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER:
            return tuple(ModelCoefficientValue(protocol.regularization.value) for protocol in DITTO_TRAINING_PROTOCOLS)
        case _:
            return (None,)


class PlanDisposition(StrEnum):
    EXECUTABLE = "executable"
    SUPPRESSED = "suppressed"
    INFEASIBLE = "infeasible"
    BLOCKED = "blocked"


class ExecutionRoute(StrEnum):
    """Execution mechanism required by one coordinate's scientific shape.

    `SINGLE_COORDINATE` is executed by `execution.execute_experiment` and
    `runner.StageRunner`. `TEMPORAL_PAIRED_EXECUTION` is executed by
    `temporal_evidence.run_temporal_future_pair`, while
    `DITTO_JOINT_PUBLICATION` is executed by
    `ditto_stress.run_ditto_stress_test_seed`. The joint routes preserve shared
    detector or related-model identities that cannot be represented safely by
    independent single-coordinate recipes.
    """

    SINGLE_COORDINATE = "single_coordinate"
    DITTO_JOINT_PUBLICATION = "ditto_joint_publication"
    TEMPORAL_PAIRED_EXECUTION = "temporal_paired_execution"


class CoordinateIdentitySegment(StrEnum):
    NO_MODEL_COEFFICIENT = "no_model_coefficient"
    NON_TEMPORAL = "non_temporal"


_DITTO_TRAINING_MODELS = frozenset(
    (TrainingModelId.DITTO_GLOBAL_AUTOENCODER, TrainingModelId.DITTO_PERSONALIZED_AUTOENCODER)
)


def execution_route_for(coordinate: ExperimentCoordinate) -> ExecutionRoute:
    if coordinate.temporal_state is not None:
        return ExecutionRoute.TEMPORAL_PAIRED_EXECUTION
    if coordinate.training_model in _DITTO_TRAINING_MODELS:
        return ExecutionRoute.DITTO_JOINT_PUBLICATION
    return ExecutionRoute.SINGLE_COORDINATE


@dataclass(frozen=True, slots=True, kw_only=True)
class PlanningEvidence:
    experiment: ExperimentId
    disposition: PlanDisposition
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("planning evidence requires a non-empty reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentCoordinate:
    experiment: ExperimentId
    evidence_role: EvidenceRole
    dataset: DatasetId
    population: PopulationId
    training_model: TrainingModelId
    training_seed: Seed
    split_protocol: SplitProtocolId
    preprocessing_protocol: PreprocessingProtocolId
    model_coefficient: ModelCoefficientValue | None
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    temporal_state: TemporalState | None

    def __post_init__(self) -> None:
        requires_coefficient = self.training_model in _MODEL_COEFFICIENT_TRAINING_MODELS
        if requires_coefficient and self.model_coefficient is None:
            raise ValueError("training models with a declared coefficient grid require a model coefficient")
        if not requires_coefficient and self.model_coefficient is not None:
            raise ValueError("a model coefficient is only active for training models with a declared coefficient grid")

    @property
    def stable_key(self) -> str:
        temporal = (
            self.temporal_state.value
            if self.temporal_state is not None
            else CoordinateIdentitySegment.NON_TEMPORAL.value
        )
        coefficient = (
            f"{self.model_coefficient.value}"
            if self.model_coefficient is not None
            else CoordinateIdentitySegment.NO_MODEL_COEFFICIENT.value
        )
        return "/".join(
            (
                self.experiment.value,
                self.evidence_role.value,
                self.dataset.value,
                self.population.value,
                self.training_model.value,
                str(self.training_seed.value),
                self.split_protocol.value,
                self.preprocessing_protocol.value,
                coefficient,
                self.threshold_method.value,
                self.metric.value,
                temporal,
            )
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PlannedExperiment:
    coordinate: ExperimentCoordinate
    disposition: PlanDisposition
    reason: str

    def __post_init__(self) -> None:
        if not self.reason.strip():
            raise ValueError("planned experiments require a non-empty reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExperimentPlan:
    entries: tuple[PlannedExperiment, ...]
    digest: str

    def __post_init__(self) -> None:
        keys = tuple(entry.coordinate.stable_key for entry in self.entries)
        if keys != tuple(sorted(keys)):
            raise ValueError("experiment-plan entries must be in deterministic order")
        if len(keys) != len(frozenset(keys)):
            raise ValueError("experiment-plan coordinates must be unique")
        if self.digest != _digest_entries(self.entries):
            raise ValueError("experiment-plan digest does not match its entries")

    @property
    def executable(self) -> tuple[PlannedExperiment, ...]:
        return tuple(entry for entry in self.entries if entry.disposition is PlanDisposition.EXECUTABLE)


def expand_experiment_plan(
    *,
    declarations: tuple[ExperimentDeclaration, ...] = EXPERIMENTS,
    seed_cohort: SeedCohort = CONFIRMATORY_SEED_COHORT,
    evidence: tuple[PlanningEvidence, ...] = (),
) -> ExperimentPlan:
    validated_evidence = _validated_evidence(evidence)
    entries = tuple(
        sorted(
            (
                _planned_entry(declaration, cell, validated_evidence)
                for declaration in declarations
                for cell in _swept_cells(declaration, seed_cohort)
            ),
            key=lambda entry: entry.coordinate.stable_key,
        )
    )
    return ExperimentPlan(entries=entries, digest=_digest_entries(entries))


@dataclass(frozen=True, slots=True, kw_only=True)
class _SweptCell:
    seed: Seed
    threshold_method: FederatedThresholdMethod
    metric: MetricId
    temporal_state: TemporalState | None
    model_coefficient: ModelCoefficientValue | None


def _swept_cells(declaration: ExperimentDeclaration, seed_cohort: SeedCohort) -> tuple[_SweptCell, ...]:
    return tuple(
        _SweptCell(
            seed=seed,
            threshold_method=threshold_method,
            metric=metric,
            temporal_state=temporal_state,
            model_coefficient=model_coefficient,
        )
        for seed in seed_cohort.values
        for threshold_method in declaration.federated_thresholds
        for metric in declaration.metrics
        for temporal_state in _temporal_states(declaration.id)
        for model_coefficient in _declared_model_coefficients(declaration.training_model)
    )


def _planned_entry(
    declaration: ExperimentDeclaration,
    cell: _SweptCell,
    evidence: tuple[PlanningEvidence, ...],
) -> PlannedExperiment:
    disposition, reason = _resolve_disposition(declaration, evidence)
    population = population_declaration(declaration.population)
    return PlannedExperiment(
        coordinate=ExperimentCoordinate(
            experiment=declaration.id,
            evidence_role=declaration.role,
            dataset=population.dataset,
            population=declaration.population,
            training_model=declaration.training_model,
            training_seed=cell.seed,
            split_protocol=split_protocol_for_population(declaration.population),
            preprocessing_protocol=SCIENTIFIC_FEDERATED_PREPROCESSING_METHOD.identity,
            model_coefficient=cell.model_coefficient,
            threshold_method=cell.threshold_method,
            metric=cell.metric,
            temporal_state=cell.temporal_state,
        ),
        disposition=disposition,
        reason=reason,
    )


def _temporal_states(experiment: ExperimentId) -> tuple[TemporalState | None, ...]:
    matches = tuple(
        declaration.temporal_states
        for declaration in EXECUTION_IDENTITY_DECLARATIONS
        if declaration.experiment is experiment
    )
    if not matches:
        return (None,)
    if len(matches) != 1:
        raise ValueError("experiment temporal-state declaration must resolve exactly once")
    return matches[0]


def _resolve_disposition(
    declaration: ExperimentDeclaration,
    evidence: tuple[PlanningEvidence, ...],
) -> tuple[PlanDisposition, str]:
    explicit = tuple(item for item in evidence if item.experiment is declaration.id)
    if explicit:
        item = explicit[0]
        return item.disposition, item.reason
    match declaration.readiness:
        case ExperimentReadiness.EXECUTABLE:
            return PlanDisposition.EXECUTABLE, "declared executable by the validated protocol graph"
        case ExperimentReadiness.SUPPRESSED:
            return PlanDisposition.SUPPRESSED, "suppressed by the validated protocol graph"
        case ExperimentReadiness.INFEASIBLE:
            return PlanDisposition.INFEASIBLE, "declared infeasible by the validated protocol graph"
        case ExperimentReadiness.BLOCKED:
            return PlanDisposition.BLOCKED, "blocked by an unresolved scientific or artifact prerequisite"
        case ExperimentReadiness.DECLARED:
            return PlanDisposition.BLOCKED, "declared experiment requires explicit feasibility evidence"


def _validated_evidence(evidence: tuple[PlanningEvidence, ...]) -> tuple[PlanningEvidence, ...]:
    experiments = tuple(item.experiment for item in evidence)
    if len(experiments) != len(frozenset(experiments)):
        raise ValueError("planning evidence must be unique by experiment")
    return evidence


def _digest_entries(entries: tuple[PlannedExperiment, ...]) -> str:
    payload = "\n".join(
        f"{entry.coordinate.stable_key}|{entry.disposition.value}|{entry.reason}" for entry in entries
    ).encode("utf-8")
    return blake2b(payload, digest_size=32).hexdigest()


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
