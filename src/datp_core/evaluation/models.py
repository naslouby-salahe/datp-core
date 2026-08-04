"""Typed records shared by held-out federated evaluation."""

from dataclasses import dataclass, field
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
from datp_core.domain.values import Checksum, MetricValue, RowCount, ScoreValue, StableRowId, ThresholdValue
from datp_core.learning.federated.models import FederatedTrainingCoordinate
from datp_core.populations.models import ClientIdentity, PopulationOutcomeLabel
from datp_core.scoring.models import ScoreRecord


@dataclass(frozen=True, slots=True)
class HeldOutBenignScore:
    """One verified benign evaluation score with immutable score-artifact provenance."""

    client: ClientIdentity
    stable_row_id: StableRowId
    score: ScoreValue
    partition_role: PartitionRole
    outcome_label: PopulationOutcomeLabel
    score_record: ScoreRecord

    def __post_init__(self) -> None:
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
class AvailableMetric:
    """A metric with exactly one finite value and optional denominator evidence."""

    metric: MetricId
    value: MetricValue
    denominator: RowCount | None = None
    status: MetricStatus = field(init=False, default=MetricStatus.AVAILABLE)

    @property
    def reason(self) -> None:
        return None


@dataclass(frozen=True, slots=True)
class UnavailableMetric:
    """A metric with exactly one closed non-available state and reason."""

    metric: MetricId
    status: MetricStatus
    reason: MetricReason
    denominator: RowCount | None = None

    def __post_init__(self) -> None:
        if self.status is MetricStatus.AVAILABLE:
            raise ValueError("available status requires an AvailableMetric")

    @property
    def value(self) -> None:
        return None


type MetricAvailability = AvailableMetric | UnavailableMetric


def metric_by_id(metrics: tuple[MetricAvailability, ...], metric: MetricId) -> MetricAvailability:
    matches = tuple(item for item in metrics if item.metric is metric)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {metric.value} metric")
    return matches[0]


def validate_metric_set(metrics: tuple[MetricAvailability, ...], expected: frozenset[MetricId]) -> None:
    metric_ids = tuple(item.metric for item in metrics)
    if len(metric_ids) != len(frozenset(metric_ids)):
        raise ValueError("metrics must be unique by metric identity")
    if frozenset(metric_ids) != expected:
        raise ValueError("metrics do not match the declared metric identities")


@dataclass(frozen=True, slots=True)
class MetricWarning:
    code: WarningCode
    metric: MetricId
    client: ClientIdentity | None = None


@dataclass(frozen=True, slots=True)
class ConfusionCounts:
    true_negative: RowCount
    false_positive: RowCount
    true_positive: RowCount
    false_negative: RowCount
    attack_assignment_valid: bool

    def __post_init__(self) -> None:
        if not isinstance(self.attack_assignment_valid, bool):
            raise ValueError("attack assignment validity must be boolean")
        if not self.attack_assignment_valid and (self.true_positive.value or self.false_negative.value):
            raise ValueError("invalid attack assignments cannot contribute attack counts")

    @property
    def benign_denominator(self) -> RowCount:
        return self.true_negative + self.false_positive

    @property
    def attack_denominator(self) -> RowCount:
        return self.true_positive + self.false_negative

    @property
    def evaluation_row_count(self) -> RowCount:
        return self.benign_denominator + self.attack_denominator


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricResultHeader:
    coordinate: FederatedTrainingCoordinate
    threshold_method: FederatedThresholdMethod
    cohort: EvaluationCohort
    metrics: tuple[MetricAvailability, ...]
    warnings: tuple[MetricWarning, ...]
    evidence_role: EvidenceRole

    def _validate_warnings(self, valid_metrics: frozenset[MetricId]) -> None:
        warning_metrics = tuple(warning.metric for warning in self.warnings)
        if len(warning_metrics) != len(frozenset(warning_metrics)):
            raise ValueError("metric warnings must be unique by metric identity")
        if any(metric not in valid_metrics for metric in warning_metrics):
            raise ValueError("metric warnings must target a declared metric")


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientMetricResult(MetricResultHeader):
    client: ClientIdentity
    threshold: ThresholdValue
    confusion: ConfusionCounts
    evaluation_score_checksum: Checksum
    evaluation_label_checksum: Checksum
    source_row_checksum: Checksum

    def __post_init__(self) -> None:
        if self.client.population != self.coordinate.population:
            raise ValueError("metric client and coordinate populations must agree")
        validate_metric_set(self.metrics, CLIENT_METRIC_IDS)
        self._validate_warnings(CLIENT_METRIC_IDS)

    @property
    def attack_evaluable(self) -> bool:
        return self.confusion.attack_assignment_valid and isinstance(
            metric_by_id(self.metrics, MetricId.TRUE_POSITIVE_RATE), AvailableMetric
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class PopulationMetricResult(MetricResultHeader):
    candidate_client_count: RowCount
    calibration_eligible_client_count: RowCount
    fpr_evaluable_client_count: RowCount
    attack_evaluable_client_count: RowCount
    deployment_fallback_count: RowCount
    unavailable_client_count: RowCount
    excluded_clients: tuple[ClientIdentity, ...]

    def __post_init__(self) -> None:
        validate_metric_set(self.metrics, POPULATION_METRIC_IDS)
        self._validate_warnings(POPULATION_METRIC_IDS)
        if self.cohort is not EvaluationCohort.FPR_EVALUABLE:
            raise ValueError("population aggregates must be labelled as FPR-evaluable")
        if self.fpr_evaluable_client_count > self.calibration_eligible_client_count:
            raise ValueError("FPR-evaluable clients must belong to the calibration-eligible cohort")
        if self.attack_evaluable_client_count > self.calibration_eligible_client_count:
            raise ValueError("attack-evaluable clients must belong to the calibration-eligible cohort")
        if self.calibration_eligible_client_count > self.candidate_client_count:
            raise ValueError("calibration-eligible client count cannot exceed the candidate count")
        if self.deployment_fallback_count + self.unavailable_client_count > self.candidate_client_count:
            raise ValueError("excluded client counts cannot exceed the candidate count")
        excluded = tuple(client.client_id for client in self.excluded_clients)
        if len(excluded) != len(frozenset(excluded)):
            raise ValueError("excluded clients must be unique")
