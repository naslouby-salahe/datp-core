"""Immutable records shared by held-out federated evaluation."""

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.enums import (
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PartitionRole,
    WarningCode,
)
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Checksum, MetricValue, RowCount, ScoreValue, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.scoring.models import ScoreRecord


@dataclass(frozen=True, slots=True)
class HeldOutBenignScore:
    """One verified benign evaluation score with immutable score-artifact provenance."""

    client: ClientIdentity
    stable_row_id: str
    score: ScoreValue
    partition_role: PartitionRole
    outcome_label: PopulationOutcomeLabel
    score_record: ScoreRecord

    def __post_init__(self) -> None:
        if not self.stable_row_id:
            raise ScientificContractError("held-out score evidence requires a stable row identity")
        if self.partition_role is not PartitionRole.EVALUATION:
            raise ScientificContractError("held-out score evidence rejects non-evaluation score rows")
        if self.outcome_label is not PopulationOutcomeLabel.BENIGN:
            raise ScientificContractError("held-out score evidence rejects attack-labelled score rows")
        if self.score_record.partition_role is not self.partition_role:
            raise ScientificContractError("held-out score evidence score provenance has a partition-role mismatch")
        if self.score_record.scored_client != self.client:
            raise ScientificContractError("held-out score evidence score provenance has a client mismatch")


class MetricStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNDEFINED = "undefined"
    SUPPRESSED = "suppressed"
    INFEASIBLE = "infeasible"
    BLOCKED = "blocked"


class MetricReason(StrEnum):
    EMPTY_BENIGN_DENOMINATOR = "empty_benign_denominator"
    EMPTY_ATTACK_DENOMINATOR = "empty_attack_denominator"
    INVALID_ATTACK_ASSIGNMENT = "invalid_attack_assignment"
    SINGLE_CLASS_SCORES = "single_class_scores"
    UNDEFINED_CLASS_F1 = "undefined_class_f1"
    ZERO_MEAN = "zero_mean"
    NO_EVALUABLE_CLIENTS = "no_evaluable_clients"
    MISSING_CAPABILITY = "missing_capability"
    UNRESOLVED_PROTOCOL_VALUE = "unresolved_protocol_value"


CLIENT_METRIC_IDS: frozenset[MetricId] = frozenset(
    (
        MetricId.FALSE_POSITIVE_RATE,
        MetricId.TRUE_POSITIVE_RATE,
        MetricId.BALANCED_ACCURACY,
        MetricId.BINARY_MACRO_F1,
        MetricId.AUROC,
    )
)

FPR_POPULATION_METRIC_IDS: tuple[MetricId, ...] = (
    MetricId.MEAN_FPR,
    MetricId.FPR_POPULATION_STANDARD_DEVIATION,
    MetricId.FPR_COEFFICIENT_OF_VARIATION,
    MetricId.FPR_IQR,
    MetricId.FPR_RANGE,
    MetricId.WORST_CLIENT_FPR,
)

POPULATION_METRIC_IDS: frozenset[MetricId] = frozenset(
    (
        *FPR_POPULATION_METRIC_IDS,
        MetricId.TPR_COEFFICIENT_OF_VARIATION,
        MetricId.P10_BINARY_MACRO_F1,
        MetricId.WORST_CLIENT_BALANCED_ACCURACY,
        MetricId.MEAN_CLIENT_MACRO_F1,
        MetricId.POOLED_MACRO_F1,
        MetricId.MEAN_CLIENT_BALANCED_ACCURACY,
    )
)


@dataclass(frozen=True, slots=True)
class UnavailableOutcome:
    status: MetricStatus
    reason: MetricReason
    denominator: RowCount | None = None

    def __post_init__(self) -> None:
        if self.status is MetricStatus.AVAILABLE:
            raise ValueError("an unavailable outcome cannot be available")


@dataclass(frozen=True, slots=True)
class MetricAvailability:
    metric: MetricId
    status: MetricStatus
    value: MetricValue | None
    denominator: RowCount | None = None
    outcome: UnavailableOutcome | None = None

    def __post_init__(self) -> None:
        if self.status is MetricStatus.AVAILABLE:
            if self.value is None or self.outcome is not None:
                raise ValueError("available metrics require exactly one value")
        elif self.value is not None or self.outcome is None:
            raise ValueError("non-available metrics require exactly one unavailable outcome")
        elif self.outcome.status is not self.status or self.outcome.denominator != self.denominator:
            raise ValueError("metric and outcome statuses and denominators must agree")


@dataclass(frozen=True, slots=True)
class MetricWarning:
    code: WarningCode
    metric: MetricId
    client: ClientIdentity | None = None


@dataclass(frozen=True, slots=True)
class ConfusionCounts:
    true_negative: int
    false_positive: int
    true_positive: int
    false_negative: int
    attack_assignment_valid: bool

    def __post_init__(self) -> None:
        for name, value in (
            ("true_negative", self.true_negative),
            ("false_positive", self.false_positive),
            ("true_positive", self.true_positive),
            ("false_negative", self.false_negative),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if not isinstance(self.attack_assignment_valid, bool):
            raise ValueError("attack assignment validity must be boolean")
        if not self.attack_assignment_valid and (self.true_positive or self.false_negative):
            raise ValueError("invalid attack assignments cannot contribute attack counts")

    @property
    def benign_denominator(self) -> RowCount:
        return RowCount(self.true_negative + self.false_positive)

    @property
    def attack_denominator(self) -> RowCount:
        return RowCount(self.true_positive + self.false_negative)

    @property
    def evaluation_row_count(self) -> RowCount:
        return RowCount(self.benign_denominator.value + self.attack_denominator.value)


@dataclass(frozen=True, slots=True)
class ClientMetricResult:
    coordinate: FederatedTrainingCoordinate
    threshold_method: FederatedThresholdMethod
    client: ClientIdentity
    cohort: EvaluationCohort
    threshold: ThresholdValue
    confusion: ConfusionCounts
    metrics: tuple[MetricAvailability, ...]
    warnings: tuple[MetricWarning, ...]
    evidence_role: EvidenceRole
    evaluation_score_checksum: Checksum
    evaluation_label_checksum: Checksum
    source_row_checksum: Checksum

    def __post_init__(self) -> None:
        if self.client.population != self.coordinate.population:
            raise ValueError("metric client and coordinate populations must agree")
        metric_ids = tuple(item.metric for item in self.metrics)
        if len(metric_ids) != len(frozenset(metric_ids)):
            raise ValueError("client metrics must be unique by metric identity")
        if frozenset(metric_ids) != CLIENT_METRIC_IDS:
            raise ValueError("client metrics must contain exactly the declared client metric identities")
        warning_metrics = tuple(warning.metric for warning in self.warnings)
        if len(warning_metrics) != len(frozenset(warning_metrics)):
            raise ValueError("client metric warnings must be unique by metric identity")
        if any(metric not in CLIENT_METRIC_IDS for metric in warning_metrics):
            raise ValueError("client metric warnings must target a declared client metric")

    @property
    def attack_evaluable(self) -> bool:
        return self.confusion.attack_assignment_valid and any(
            metric.metric is MetricId.TRUE_POSITIVE_RATE and metric.value is not None for metric in self.metrics
        )


@dataclass(frozen=True, slots=True)
class PopulationMetricResult:
    coordinate: FederatedTrainingCoordinate
    threshold_method: FederatedThresholdMethod
    cohort: EvaluationCohort
    metrics: tuple[MetricAvailability, ...]
    candidate_client_count: RowCount
    calibration_eligible_client_count: RowCount
    fpr_evaluable_client_count: RowCount
    attack_evaluable_client_count: RowCount
    deployment_fallback_count: RowCount
    unavailable_client_count: RowCount
    excluded_clients: tuple[ClientIdentity, ...]
    warnings: tuple[MetricWarning, ...]
    evidence_role: EvidenceRole

    def __post_init__(self) -> None:
        metric_ids = tuple(item.metric for item in self.metrics)
        if len(metric_ids) != len(frozenset(metric_ids)):
            raise ValueError("population metrics must be unique by metric identity")
        if frozenset(metric_ids) != POPULATION_METRIC_IDS:
            raise ValueError("population metrics must contain exactly the declared population metric identities")
        if self.cohort is not EvaluationCohort.FPR_EVALUABLE:
            raise ValueError("population aggregates must be labelled as FPR-evaluable")
        counts = (
            self.candidate_client_count,
            self.calibration_eligible_client_count,
            self.fpr_evaluable_client_count,
            self.attack_evaluable_client_count,
            self.deployment_fallback_count,
            self.unavailable_client_count,
        )
        if any(count.value < 0 for count in counts):
            raise ValueError("population client counts must be non-negative")
        if self.fpr_evaluable_client_count.value > self.calibration_eligible_client_count.value:
            raise ValueError("FPR-evaluable clients must belong to the calibration-eligible cohort")
        if self.attack_evaluable_client_count.value > self.calibration_eligible_client_count.value:
            raise ValueError("attack-evaluable clients must belong to the calibration-eligible cohort")
        if self.calibration_eligible_client_count.value > self.candidate_client_count.value:
            raise ValueError("calibration-eligible client count cannot exceed the candidate count")
        if (
            self.deployment_fallback_count.value + self.unavailable_client_count.value
            > self.candidate_client_count.value
        ):
            raise ValueError("excluded client counts cannot exceed the candidate count")
        excluded = tuple(client.client_id for client in self.excluded_clients)
        if len(excluded) != len(frozenset(excluded)):
            raise ValueError("excluded clients must be unique")
        warning_metrics = tuple(warning.metric for warning in self.warnings)
        if len(warning_metrics) != len(frozenset(warning_metrics)):
            raise ValueError("population metric warnings must be unique by metric identity")
        if any(metric not in POPULATION_METRIC_IDS for metric in warning_metrics):
            raise ValueError("population metric warnings must target a declared population metric")


@dataclass(frozen=True, slots=True)
class CoverageResult:
    target_coverage: MetricAvailability
    achieved_held_out_benign_coverage: MetricAvailability
    signed_coverage_error: MetricAvailability
    absolute_coverage_error: MetricAvailability


@dataclass(frozen=True, slots=True)
class ThresholdEstimationResult:
    absolute_threshold_error: MetricAvailability
    relative_threshold_error: MetricAvailability
    signed_attainment_error: MetricAvailability
    absolute_attainment_error: MetricAvailability


@dataclass(frozen=True, slots=True)
class CommunicationResult:
    estimated_serialized_bytes: MetricAvailability


@dataclass(frozen=True, slots=True)
class AlertBurdenResult:
    alerts_per_client_per_day: MetricAvailability
