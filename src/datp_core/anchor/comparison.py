"""Metric-specific full-precision anchor comparison strategies."""

from dataclasses import dataclass

from datp_core.anchor.models import (
    AbsoluteToleranceRule,
    AnchorComparisonDecision,
    AnchorComparisonStrategy,
    AnchorDiscrepancyReason,
    AnchorMetricComparison,
    AnchorMetricReference,
    AnchorObservedMetric,
    AnchorToleranceRule,
    ExactCountRule,
    ExactEqualityRule,
    IntervalOverlapRule,
    RelativeToleranceRule,
    SourceDefinedRule,
)
from datp_core.domain.enums import CheckpointStatus, FederatedThresholdMethod, MetricId, PopulationId, TrainingModelId
from datp_core.domain.values import (
    MetricValue,
    floats_absolutely_close,
    floats_exactly_equal,
    is_numeric_zero,
)
from datp_core.protocols.anchor import FIXED_SCORE_ABSOLUTE_TOLERANCE


def floats_match(
    left: float,
    right: float,
    *,
    absolute_tolerance: MetricValue = FIXED_SCORE_ABSOLUTE_TOLERANCE,
) -> bool:
    """Compare floats with declared MetricValue absolute tolerance. Never use bare float equality."""
    return floats_absolutely_close(left, right, absolute_tolerance.value)


@dataclass(frozen=True, slots=True)
class _NumericDelta:
    expected: float
    observed: float

    @property
    def signed(self) -> float:
        return self.observed - self.expected

    @property
    def relative(self) -> float | None:
        if is_numeric_zero(self.expected):
            return None
        return self.signed / abs(self.expected)


@dataclass(frozen=True, slots=True)
class _ComparisonOutcome:
    decision: AnchorComparisonDecision
    reason: AnchorDiscrepancyReason | None
    signed: float | None
    relative: float | None


def compare_anchor_metric(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric | None,
) -> AnchorMetricComparison:
    """Compare one mandatory reference against an optional observation at full precision."""
    rule = reference.tolerance_rule
    if observation is None:
        return _build(
            reference,
            None,
            rule,
            _ComparisonOutcome(
                AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
                AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
                None,
                None,
            ),
        )

    coordinate_failure = _coordinate_mismatch_reason(reference, observation)
    delta = _NumericDelta(reference.value.value, observation.value.value)
    if coordinate_failure is not None:
        return _build(
            reference,
            observation,
            rule,
            _ComparisonOutcome(
                AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
                coordinate_failure,
                delta.signed,
                delta.relative,
            ),
        )
    return _compare_with_rule(reference, observation, rule, delta)


def reject_global_floating_point_tolerance() -> AnchorMetricComparison:
    """Explicit rejection of an undifferentiated global floating-point tolerance."""
    raise ValueError("global floating-point tolerance is unsupported; declare a metric-specific rule")


def full_precision_failure_stands_despite_rounded_equality(
    *,
    full_precision_decision: AnchorComparisonDecision,
    presentation_decimals: int,
    expected: float,
    observed: float,
) -> bool:
    """Return True when rounded presentation equality must not rescue a full-precision failure."""
    if presentation_decimals < 0:
        raise ValueError("presentation decimals must be non-negative")
    if full_precision_decision is AnchorComparisonDecision.EQUIVALENT:
        return False
    return floats_exactly_equal(round(expected, presentation_decimals), round(observed, presentation_decimals))


def values_within_absolute_tolerance(expected: float, observed: float, absolute_tolerance: MetricValue) -> bool:
    return floats_match(expected, observed, absolute_tolerance=absolute_tolerance)


def strategy_of(rule: AnchorToleranceRule) -> AnchorComparisonStrategy:
    return rule.strategy


def _compare_with_rule(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: AnchorToleranceRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    match rule:
        case ExactEqualityRule() | SourceDefinedRule():
            return _equality_result(reference, observation, rule, delta)
        case AbsoluteToleranceRule(absolute_tolerance=tolerance):
            if floats_match(delta.expected, delta.observed, absolute_tolerance=tolerance):
                return _pass(reference, observation, rule, delta)
            return _fail(
                reference,
                observation,
                rule,
                delta,
                AnchorDiscrepancyReason.ABSOLUTE_TOLERANCE_EXCEEDED,
            )
        case RelativeToleranceRule():
            return _relative_result(reference, observation, rule, delta)
        case IntervalOverlapRule():
            return _interval_result(reference, observation, rule, delta)
        case ExactCountRule():
            return _count_result(reference, observation, rule, delta)
        case _:
            raise ValueError(f"unsupported tolerance rule strategy {rule.strategy}")


def _equality_result(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: AnchorToleranceRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    if floats_exactly_equal(delta.expected, delta.observed):
        return _pass(reference, observation, rule, delta)
    return _fail(reference, observation, rule, delta, AnchorDiscrepancyReason.EXACT_MISMATCH)


def _relative_result(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: RelativeToleranceRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    if is_numeric_zero(delta.expected):
        return _build(
            reference,
            observation,
            rule,
            _ComparisonOutcome(
                AnchorComparisonDecision.UNAVAILABLE,
                AnchorDiscrepancyReason.RELATIVE_COMPARISON_UNDEFINED_FOR_ZERO_REFERENCE,
                delta.signed,
                None,
            ),
        )
    if delta.relative is not None and abs(delta.relative) <= rule.relative_tolerance.value:
        return _pass(reference, observation, rule, delta)
    return _fail(reference, observation, rule, delta, AnchorDiscrepancyReason.RELATIVE_TOLERANCE_EXCEEDED)


def _interval_result(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: IntervalOverlapRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    if reference.interval is None or observation.interval is None:
        return _build(
            reference,
            observation,
            rule,
            _ComparisonOutcome(
                AnchorComparisonDecision.UNAVAILABLE,
                AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
                delta.signed,
                delta.relative,
            ),
        )
    left = reference.interval
    right = observation.interval
    lower_bound = max(left.lower.value, right.lower.value)
    upper_bound = min(left.upper.value, right.upper.value)
    overlaps = lower_bound < upper_bound or floats_exactly_equal(lower_bound, upper_bound)
    if overlaps:
        return _pass(reference, observation, rule, delta)
    return _fail(reference, observation, rule, delta, AnchorDiscrepancyReason.INTERVAL_NO_OVERLAP)


def _count_result(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: ExactCountRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    if reference.count is None or observation.count is None:
        return _build(
            reference,
            observation,
            rule,
            _ComparisonOutcome(
                AnchorComparisonDecision.UNAVAILABLE,
                AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
                delta.signed,
                delta.relative,
            ),
        )
    if reference.count == observation.count:
        return _pass(reference, observation, rule, delta)
    return _build(
        reference,
        observation,
        rule,
        _ComparisonOutcome(
            AnchorComparisonDecision.MATERIAL_DISCREPANCY,
            AnchorDiscrepancyReason.COUNT_MISMATCH,
            float(observation.count.value - reference.count.value),
            delta.relative,
        ),
    )


def _coordinate_mismatch_reason(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
) -> AnchorDiscrepancyReason | None:
    checks: tuple[tuple[bool, AnchorDiscrepancyReason], ...] = (
        (observation.seed != reference.seed, AnchorDiscrepancyReason.WRONG_SEED_SUBSET),
        (observation.population is not reference.population, AnchorDiscrepancyReason.WRONG_POPULATION),
        (observation.training_model is not reference.training_model, AnchorDiscrepancyReason.WRONG_TRAINING_MODEL),
        (
            observation.threshold_method is not reference.threshold_method,
            AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD,
        ),
        (observation.metric is not reference.metric, AnchorDiscrepancyReason.WRONG_METRIC),
        (
            observation.checkpoint_status is not reference.checkpoint_status,
            AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS,
        ),
        (
            observation.checkpoint_status is not CheckpointStatus.HISTORICAL_ENDPOINT,
            AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS,
        ),
        (
            observation.population is not PopulationId.NBAIOT_NATURAL_DEVICES,
            AnchorDiscrepancyReason.WRONG_POPULATION,
        ),
        (
            observation.training_model is not TrainingModelId.FEDAVG_AUTOENCODER,
            AnchorDiscrepancyReason.WRONG_TRAINING_MODEL,
        ),
        (
            observation.threshold_method
            not in {
                FederatedThresholdMethod.SHARED_THRESHOLD,
                FederatedThresholdMethod.LOCAL_THRESHOLD,
            },
            AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD,
        ),
        (
            observation.metric is not MetricId.FPR_COEFFICIENT_OF_VARIATION,
            AnchorDiscrepancyReason.WRONG_METRIC,
        ),
    )
    for failed, reason in checks:
        if failed:
            return reason
    return None


def _pass(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: AnchorToleranceRule,
    delta: _NumericDelta,
) -> AnchorMetricComparison:
    return _build(
        reference,
        observation,
        rule,
        _ComparisonOutcome(AnchorComparisonDecision.EQUIVALENT, None, delta.signed, delta.relative),
    )


def _fail(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
    rule: AnchorToleranceRule,
    delta: _NumericDelta,
    reason: AnchorDiscrepancyReason,
) -> AnchorMetricComparison:
    return _build(
        reference,
        observation,
        rule,
        _ComparisonOutcome(
            AnchorComparisonDecision.MATERIAL_DISCREPANCY,
            reason,
            delta.signed,
            delta.relative,
        ),
    )


def _build(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric | None,
    rule: AnchorToleranceRule,
    outcome: _ComparisonOutcome,
) -> AnchorMetricComparison:
    return AnchorMetricComparison(
        reference=reference,
        observation=observation,
        decision=outcome.decision,
        signed_difference=outcome.signed,
        relative_difference=outcome.relative,
        tolerance_rule=rule,
        reason=outcome.reason,
    )
