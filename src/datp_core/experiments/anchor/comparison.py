from datp_core.core.numeric import MetricDelta, floats_absolutely_close, floats_exactly_equal, is_numeric_zero
from datp_core.experiments.anchor.contracts import (
    AbsoluteToleranceRule,
    AnchorComparisonDecision,
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


class _NumericDelta:
    __slots__ = ("expected", "observed", "signed", "relative")

    def __init__(self, expected: float, observed: float):
        self.expected = expected
        self.observed = observed
        self.signed = observed - expected
        self.relative = None if is_numeric_zero(expected) else (self.signed / abs(expected))


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
            decision=AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
        )

    coordinate_failure = _coordinate_mismatch_reason(reference, observation)
    delta = _NumericDelta(reference.value.value, observation.value.value)

    if coordinate_failure is not None:
        return _build(
            reference,
            observation,
            rule,
            decision=AnchorComparisonDecision.BLOCKED_INVALID_INPUT,
            reason=coordinate_failure,
            signed=delta.signed,
            relative=delta.relative,
        )
    return _compare_with_rule(reference, observation, rule, delta)


def reject_global_floating_point_tolerance() -> None:
    """Explicit rejection of an undifferentiated global floating-point tolerance."""
    raise ValueError("global floating-point tolerance is unsupported; declare a metric-specific rule")


def full_precision_failure_stands_despite_rounded_equality(
    *,
    full_precision_decision: AnchorComparisonDecision,
    presentation_decimals: int,  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    expected: float,  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    observed: float,  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
) -> bool:
    """Return True when rounded presentation equality must not rescue a full-precision failure."""
    if presentation_decimals < 0:
        raise ValueError("presentation decimals must be non-negative")
    if full_precision_decision is AnchorComparisonDecision.EQUIVALENT:
        return False
    return floats_exactly_equal(round(expected, presentation_decimals), round(observed, presentation_decimals))


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
            if floats_absolutely_close(delta.expected, delta.observed, tolerance.value):
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
    if delta.relative is None:
        return _build(
            reference,
            observation,
            rule,
            decision=AnchorComparisonDecision.UNAVAILABLE,
            reason=AnchorDiscrepancyReason.RELATIVE_COMPARISON_UNDEFINED_FOR_ZERO_REFERENCE,
            signed=delta.signed,
        )
    if abs(delta.relative) <= rule.relative_tolerance.value:
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
            decision=AnchorComparisonDecision.UNAVAILABLE,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
            signed=delta.signed,
            relative=delta.relative,
        )

    left = reference.interval
    right = observation.interval
    lower_bound = max(left.lower.value, right.lower.value)
    upper_bound = min(left.upper.value, right.upper.value)

    if lower_bound <= upper_bound or floats_exactly_equal(lower_bound, upper_bound):
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
            decision=AnchorComparisonDecision.UNAVAILABLE,
            reason=AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION,
            signed=delta.signed,
            relative=delta.relative,
        )
    if reference.count == observation.count:
        return _pass(reference, observation, rule, delta)
    return _build(
        reference,
        observation,
        rule,
        decision=AnchorComparisonDecision.MATERIAL_DISCREPANCY,
        reason=AnchorDiscrepancyReason.COUNT_MISMATCH,
        signed=float(observation.count.value - reference.count.value),
        relative=delta.relative,
    )


def _coordinate_mismatch_reason(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric,
) -> AnchorDiscrepancyReason | None:
    if observation.seed != reference.seed:
        return AnchorDiscrepancyReason.WRONG_SEED_SUBSET
    if observation.population is not reference.population:
        return AnchorDiscrepancyReason.WRONG_POPULATION
    if observation.training_model is not reference.training_model:
        return AnchorDiscrepancyReason.WRONG_TRAINING_MODEL
    if observation.threshold_method is not reference.threshold_method:
        return AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD
    if observation.metric is not reference.metric:
        return AnchorDiscrepancyReason.WRONG_METRIC
    if observation.checkpoint_status is not reference.checkpoint_status:
        return AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS
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
        decision=AnchorComparisonDecision.EQUIVALENT,
        signed=delta.signed,
        relative=delta.relative,
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
        decision=AnchorComparisonDecision.MATERIAL_DISCREPANCY,
        reason=reason,
        signed=delta.signed,
        relative=delta.relative,
    )


def _build(
    reference: AnchorMetricReference,
    observation: AnchorObservedMetric | None,
    rule: AnchorToleranceRule,
    *,
    decision: AnchorComparisonDecision,
    reason: AnchorDiscrepancyReason | None = None,
    signed: float
    | None = None,  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    relative: float
    | None = None,  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
) -> AnchorMetricComparison:
    return AnchorMetricComparison(
        reference=reference,
        observation=observation,
        decision=decision,
        signed_difference=None if signed is None else MetricDelta(signed),
        relative_difference=None if relative is None else MetricDelta(relative),
        tolerance_rule=rule,
        reason=reason,
    )
