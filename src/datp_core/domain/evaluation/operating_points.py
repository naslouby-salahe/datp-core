from dataclasses import dataclass
from enum import StrEnum
from math import isclose, isfinite, sqrt

from datp_core.domain.artifacts.references import StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import (
    CalibrationSampleCountRef,
    CitedTrafficRateEvidence,
    ConfusionCount,
    MeasuredTrafficRateEvidence,
    SampleCount,
    TrafficRateEvidence,
)
from datp_core.domain.evaluation.metrics import MetricId, MetricSpec, OperatingPointMetric
from datp_core.domain.evaluation.statistical_results import (
    AuRocScore,
    ClaimOutcome,
    EligibilityCoverage,
    FalsePositiveRate,
    TruePositiveRate,
)
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientRoster
from datp_core.domain.thresholding.policies import CoreThresholdPolicy, ThresholdValue


class ClientEligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    FALLBACK_ASSIGNED = "fallback_assigned"
    EXCLUDED = "excluded"


class ClientEligibilityReason(StrEnum):
    SUFFICIENT_CALIBRATION = "sufficient_calibration"
    INSUFFICIENT_CALIBRATION_GLOBAL_FALLBACK = "insufficient_calibration_global_fallback"
    MISSING_TEST_BENIGN = "missing_test_benign"
    MISSING_TEST_ATTACK = "missing_test_attack"


class ZeroDenominatorPolicy(StrEnum):
    ZERO = "zero"


@dataclass(frozen=True, slots=True, kw_only=True)
class StandardEvaluationSuiteSpec:
    primary_metric: OperatingPointMetric
    metrics: tuple[MetricSpec, ...]

    def __post_init__(self) -> None:
        if not _is_valid_evaluation_suite(self.primary_metric, self.metrics, requires_alert_burden=False):
            raise DomainValidationError(
                detail="standard evaluation requires CV(FPR) as its primary metric and no alert-burden metric",
                value=repr(self),
                constraint="primary CV_FPR; unique MetricSpec values; ALERT_BURDEN requires evidence variant",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class AlertBurdenEvaluationSuiteSpec:
    primary_metric: OperatingPointMetric
    metrics: tuple[MetricSpec, ...]
    traffic_rate_evidence: TrafficRateEvidence

    def __post_init__(self) -> None:
        if not _is_valid_alert_burden_evaluation_suite(self):
            raise DomainValidationError(
                detail="alert-burden evaluation requires CV(FPR), the alert metric, and typed traffic evidence",
                value=repr(self),
                constraint="CV_FPR, ALERT_BURDEN, and TrafficRateEvidence",
            )


def _is_valid_evaluation_suite(
    primary_metric: OperatingPointMetric,
    metrics: tuple[MetricSpec, ...],
    *,
    requires_alert_burden: bool,
) -> bool:
    metric_ids = tuple(specification.metric for specification in metrics)
    return all(
        (
            primary_metric is OperatingPointMetric.CV_FPR,
            bool(metrics),
            len(set(metric_ids)) == len(metric_ids),
            primary_metric in metric_ids,
            _has_expected_alert_burden_metric(metric_ids, requires_alert_burden),
        )
    )


def _has_expected_alert_burden_metric(
    metric_ids: tuple[MetricId, ...],
    requires_alert_burden: bool,
) -> bool:
    return (OperatingPointMetric.ALERT_BURDEN in metric_ids) is requires_alert_burden


def _is_valid_alert_burden_evaluation_suite(specification: AlertBurdenEvaluationSuiteSpec) -> bool:
    return _is_valid_evaluation_suite(
        specification.primary_metric,
        specification.metrics,
        requires_alert_burden=True,
    ) and type(specification.traffic_rate_evidence) in {MeasuredTrafficRateEvidence, CitedTrafficRateEvidence}


type EvaluationSuiteSpec = StandardEvaluationSuiteSpec | AlertBurdenEvaluationSuiteSpec


@dataclass(frozen=True, slots=True, kw_only=True)
class PrecisionScore:
    value: float

    def __post_init__(self) -> None:
        _validate_unit_interval(value=self.value, name="precision")


@dataclass(frozen=True, slots=True, kw_only=True)
class RecallScore:
    value: float

    def __post_init__(self) -> None:
        _validate_unit_interval(value=self.value, name="recall")


@dataclass(frozen=True, slots=True, kw_only=True)
class F1Score:
    value: float

    def __post_init__(self) -> None:
        _validate_unit_interval(value=self.value, name="F1")


@dataclass(frozen=True, slots=True, kw_only=True)
class BalancedAccuracyScore:
    value: float

    def __post_init__(self) -> None:
        _validate_unit_interval(value=self.value, name="balanced accuracy")


def _validate_unit_interval(*, value: object, name: str) -> None:
    if not isinstance(value, int | float) or isinstance(value, bool):
        raise DomainValidationError(
            detail=f"{name} must be a finite value between zero and one",
            value=repr(value),
            constraint="finite 0 <= value <= 1",
        )
    if not isfinite(value) or not 0 <= value <= 1:
        raise DomainValidationError(
            detail=f"{name} must be a finite value between zero and one",
            value=repr(value),
            constraint="finite 0 <= value <= 1",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class IneligibleClientReason:
    client_id: ClientId
    reason: ClientEligibilityReason


@dataclass(frozen=True, slots=True, kw_only=True)
class EligibleClientSet:
    roster: ClientRoster
    protocol_eligibility_rule_identity: StageFingerprint
    eligible_clients: tuple[ClientId, ...]
    ineligible_reasons: tuple[IneligibleClientReason, ...]
    identity: StageFingerprint

    def __post_init__(self) -> None:
        if not _is_valid_eligible_client_set(self):
            raise DomainValidationError(
                detail="eligible client set must partition its roster once in canonical order",
                value=repr(self),
                constraint="one ordered eligible or ineligible record for every roster client",
            )


def _is_valid_eligible_client_set(client_set: EligibleClientSet) -> bool:
    ineligible_clients = tuple(item.client_id for item in client_set.ineligible_reasons)
    return all(
        (
            _has_eligible_client_set_component_types(client_set),
            _has_canonical_eligible_clients(client_set.eligible_clients),
            not set(client_set.eligible_clients).intersection(ineligible_clients),
            set(client_set.eligible_clients).union(ineligible_clients) == set(client_set.roster.client_ids),
        )
    )


def _has_eligible_client_set_component_types(client_set: EligibleClientSet) -> bool:
    return all(
        (
            type(client_set.roster) is ClientRoster,
            type(client_set.protocol_eligibility_rule_identity) is StageFingerprint,
            type(client_set.identity) is StageFingerprint,
        )
    )


def _has_canonical_eligible_clients(clients: tuple[ClientId, ...]) -> bool:
    return (
        bool(clients)
        and clients == tuple(sorted(clients, key=lambda client: client.value))
        and len(set(clients)) == len(clients)
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientEvaluationResult:
    client_id: ClientId
    true_positive: ConfusionCount
    false_positive: ConfusionCount
    true_negative: ConfusionCount
    false_negative: ConfusionCount
    benign_test_count: SampleCount
    attack_test_count: SampleCount
    assigned_threshold: ThresholdValue
    false_positive_rate: FalsePositiveRate
    true_positive_rate: TruePositiveRate
    precision: PrecisionScore
    recall: RecallScore
    f1: F1Score
    balanced_accuracy: BalancedAccuracyScore
    eligibility_status: ClientEligibilityStatus
    eligibility_reason: ClientEligibilityReason
    calibration_sample_count_reference: CalibrationSampleCountRef
    eligible_client_set_identity: StageFingerprint
    fallback_fingerprint: StageFingerprint
    test_split_identity: StageFingerprint
    zero_denominator_policy: ZeroDenominatorPolicy

    def __post_init__(self) -> None:
        if not _is_valid_client_evaluation_result(self):
            raise DomainValidationError(
                detail="client evaluation must retain coherent counts, lineage, policy, and derived metrics",
                value=repr(self),
                constraint="counts, calibration identity, policy, and recomputable metrics",
            )


def _is_valid_client_evaluation_result(result: ClientEvaluationResult) -> bool:
    return all(
        (
            _has_consistent_evaluation_counts(result),
            result.client_id == result.calibration_sample_count_reference.client_id,
            type(result.zero_denominator_policy) is ZeroDenominatorPolicy,
            _has_recomputable_evaluation_metrics(result),
        )
    )


def _has_consistent_evaluation_counts(result: ClientEvaluationResult) -> bool:
    return all(
        (
            result.benign_test_count.value == result.true_negative.value + result.false_positive.value,
            result.attack_test_count.value == result.true_positive.value + result.false_negative.value,
        )
    )


def _has_recomputable_evaluation_metrics(result: ClientEvaluationResult) -> bool:
    expected_fpr = _ratio(numerator=result.false_positive.value, denominator=result.benign_test_count.value)
    expected_tpr = _ratio(numerator=result.true_positive.value, denominator=result.attack_test_count.value)
    expected_precision = _ratio(
        numerator=result.true_positive.value,
        denominator=result.true_positive.value + result.false_positive.value,
    )
    expected_f1 = _ratio(
        numerator=2 * result.true_positive.value,
        denominator=2 * result.true_positive.value + result.false_positive.value + result.false_negative.value,
    )
    expected_balanced_accuracy = (expected_tpr + (1 - expected_fpr)) / 2
    return all(
        isclose(actual, expected, rel_tol=0, abs_tol=1e-12)
        for actual, expected in zip(
            (
                result.false_positive_rate.value,
                result.true_positive_rate.value,
                result.precision.value,
                result.recall.value,
                result.f1.value,
                result.balanced_accuracy.value,
            ),
            (expected_fpr, expected_tpr, expected_precision, expected_tpr, expected_f1, expected_balanced_accuracy),
            strict=True,
        )
    )


def _ratio(*, numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidCvResult:
    point_estimate: float
    affected_scope_identity: StageFingerprint

    def __post_init__(self) -> None:
        if (
            not isfinite(self.point_estimate)
            or self.point_estimate < 0
            or type(self.affected_scope_identity) is not StageFingerprint
        ):
            raise DomainValidationError(
                detail="valid CV result requires a finite non-negative estimate and typed scope",
                value=repr(self),
                constraint="finite CV >= 0 and StageFingerprint",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class UndefinedCvResult:
    reason: str
    mean_value: float
    iqr: float
    value_range: float
    affected_scope_identity: StageFingerprint
    wording_outcome: ClaimOutcome

    def __post_init__(self) -> None:
        if not _is_valid_undefined_cv_result(self):
            raise DomainValidationError(
                detail="undefined CV result requires zero mean, absolute companions, scope, and wording outcome",
                value=repr(self),
                constraint="zero mean with finite non-negative IQR/range and typed metadata",
            )


def _is_valid_undefined_cv_result(result: UndefinedCvResult) -> bool:
    return all(
        (
            type(result.reason) is str,
            bool(result.reason),
            result.mean_value == 0,
            _are_finite_non_negative(result.iqr, result.value_range),
            type(result.affected_scope_identity) is StageFingerprint,
            type(result.wording_outcome) is ClaimOutcome,
        )
    )


def _are_finite_non_negative(*values: float) -> bool:
    return all(isfinite(value) and value >= 0 for value in values)


type CvOutcome = ValidCvResult | UndefinedCvResult


def cv_outcome(
    *, values: tuple[float, ...], affected_scope_identity: StageFingerprint, wording_outcome: ClaimOutcome
) -> CvOutcome:
    if not _has_valid_cv_values(values):
        raise DomainValidationError(
            detail="CV requires a non-empty tuple of finite non-negative rates",
            value=repr(values),
            constraint="non-empty finite non-negative rate tuple",
        )
    mean_value, iqr, value_range = _cv_summary(values)
    if mean_value == 0:
        return UndefinedCvResult(
            reason="zero_mean_rate",
            mean_value=mean_value,
            iqr=iqr,
            value_range=value_range,
            affected_scope_identity=affected_scope_identity,
            wording_outcome=wording_outcome,
        )
    return _valid_cv_result(values, mean_value, affected_scope_identity)


def _has_valid_cv_values(values: tuple[float, ...]) -> bool:
    return bool(values) and _are_finite_non_negative(*values)


def _cv_summary(values: tuple[float, ...]) -> tuple[float, float, float]:
    mean_value = sum(values) / len(values)
    ordered_values = tuple(sorted(values))
    value_range = ordered_values[-1] - ordered_values[0]
    middle = len(ordered_values) // 2
    lower = ordered_values[:middle]
    upper = ordered_values[-middle:]
    iqr = _interquartile_range(lower, upper)
    return mean_value, iqr, value_range


def _interquartile_range(lower: tuple[float, ...], upper: tuple[float, ...]) -> float:
    if not lower:
        return 0.0
    return sum(upper) / len(upper) - sum(lower) / len(lower)


def _valid_cv_result(
    values: tuple[float, ...], mean_value: float, affected_scope_identity: StageFingerprint
) -> ValidCvResult:
    variance = sum((value - mean_value) ** 2 for value in values) / len(values)
    return ValidCvResult(point_estimate=sqrt(variance) / mean_value, affected_scope_identity=affected_scope_identity)


@dataclass(frozen=True, slots=True, kw_only=True)
class EligibilityCoverageResult:
    eligible_count: int
    roster_count: int
    coverage: EligibilityCoverage
    eligible_client_set_identity: StageFingerprint

    def __post_init__(self) -> None:
        if (
            self.roster_count < 1
            or not 0 <= self.eligible_count <= self.roster_count
            or self.coverage.value != self.eligible_count / self.roster_count
        ):
            raise DomainValidationError(
                detail="eligibility coverage must exactly match eligible and roster counts",
                value=repr(self),
                constraint="coverage == eligible_count / roster_count",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ConformalCoverageResult:
    empirical_coverage: float
    target_coverage: float
    conformal_split_identity: StageFingerprint

    def __post_init__(self) -> None:
        _validate_unit_interval(value=self.empirical_coverage, name="empirical conformal coverage")
        _validate_unit_interval(value=self.target_coverage, name="target conformal coverage")
        if type(self.conformal_split_identity) is not StageFingerprint:
            raise DomainValidationError(
                detail="conformal coverage requires split identity", value=repr(self), constraint="StageFingerprint"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FleetDispersionResult:
    cv_fpr: CvOutcome
    cv_tpr: CvOutcome
    iqr_fpr: float
    fpr_range: float
    worst_client_fpr: FalsePositiveRate
    eligibility_coverage: EligibilityCoverageResult

    def __post_init__(self) -> None:
        if any(not isfinite(value) or value < 0 for value in (self.iqr_fpr, self.fpr_range)):
            raise DomainValidationError(
                detail="fleet dispersion companions must be finite and non-negative",
                value=repr(self),
                constraint="finite IQR and range >= 0",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class FleetDetectionResult:
    macro_f1: F1Score
    p10_macro_f1: F1Score
    worst_client_balanced_accuracy: BalancedAccuracyScore
    auroc_control: AuRocScore


@dataclass(frozen=True, slots=True, kw_only=True)
class FleetEquityResult:
    jain_index: float
    gini_coefficient: float

    def __post_init__(self) -> None:
        _validate_unit_interval(value=self.jain_index, name="Jain index")
        _validate_unit_interval(value=self.gini_coefficient, name="Gini coefficient")


@dataclass(frozen=True, slots=True, kw_only=True)
class ClusterDispersionResult:
    within_cluster_dispersion: float
    across_cluster_dispersion: float
    adjusted_rand_stability: float

    def __post_init__(self) -> None:
        if any(
            not isfinite(value) or value < 0
            for value in (self.within_cluster_dispersion, self.across_cluster_dispersion)
        ):
            raise DomainValidationError(
                detail="cluster dispersion values must be finite and non-negative",
                value=repr(self),
                constraint="finite dispersion values >= 0",
            )
        if not -1 <= self.adjusted_rand_stability <= 1:
            raise DomainValidationError(
                detail="adjusted-Rand stability must be between minus one and one",
                value=repr(self.adjusted_rand_stability),
                constraint="-1 <= adjusted Rand <= 1",
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class PolicyEvaluationResult:
    policy: CoreThresholdPolicy
    evaluation_identity: StageFingerprint
    eligible_client_set: EligibleClientSet
    client_results: tuple[ClientEvaluationResult, ...]
    fleet_dispersion: FleetDispersionResult
    fleet_detection: FleetDetectionResult
    fleet_equity: FleetEquityResult | None
    cluster_dispersion: ClusterDispersionResult | None

    def __post_init__(self) -> None:
        if not _is_valid_policy_evaluation_result(self):
            raise DomainValidationError(
                detail="policy evaluation must preserve one paired eligible-client-set identity for its full roster",
                value=repr(self),
                constraint="ordered complete roster with one EligibleClientSet identity",
            )


def _is_valid_policy_evaluation_result(result: PolicyEvaluationResult) -> bool:
    clients = tuple(client_result.client_id for client_result in result.client_results)
    return all(
        (
            bool(clients),
            clients == result.eligible_client_set.roster.client_ids,
            _has_matching_eligible_client_set_identity(result),
        )
    )


def _has_matching_eligible_client_set_identity(result: PolicyEvaluationResult) -> bool:
    return all(
        client_result.eligible_client_set_identity == result.eligible_client_set.identity
        for client_result in result.client_results
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class TemporalPolicyEvaluationResult:
    temporal_score_identity: StageFingerprint
    temporal_window_identity: StageFingerprint
    assignment_identity: StageFingerprint
    policy_evaluation: PolicyEvaluationResult
