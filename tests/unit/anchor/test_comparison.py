import pytest
from tests.unit.anchor.helpers import make_observation, make_reference

from datp_core.anchor.comparison import (
    AbsoluteToleranceRule,
    AnchorComparisonDecision,
    AnchorDiscrepancyReason,
    ExactCountRule,
    IntervalOverlapRule,
    MetricInterval,
    RelativeToleranceRule,
    compare_anchor_metric,
    full_precision_failure_stands_despite_rounded_equality,
    reject_global_floating_point_tolerance,
)
from datp_core.domain.enums import (
    CheckpointStatus,
    FederatedThresholdMethod,
    PopulationId,
    TrainingModelId,
)
from datp_core.domain.values.counts import ClientCount
from datp_core.domain.values.ratios import MetricValue


def test_exact_reproduction_passes() -> None:
    comparison = compare_anchor_metric(
        make_reference(value=1.0448312675151203), make_observation(value=1.0448312675151203)
    )
    assert comparison.decision is AnchorComparisonDecision.EQUIVALENT
    assert comparison.signed_difference is not None
    assert comparison.signed_difference.value == 0.0


def test_absolute_tolerance_passes_within_declared_bound() -> None:
    rule = AbsoluteToleranceRule(absolute_tolerance=MetricValue(1e-12))
    comparison = compare_anchor_metric(
        make_reference(value=1.0, rule=rule),
        make_observation(value=1.0 + 5e-13),
    )
    assert comparison.decision is AnchorComparisonDecision.EQUIVALENT


def test_relative_tolerance_passes_within_declared_bound() -> None:
    rule = RelativeToleranceRule(relative_tolerance=MetricValue(1e-6))
    comparison = compare_anchor_metric(
        make_reference(value=2.0, rule=rule),
        make_observation(value=2.0 + 1e-9),
    )
    assert comparison.decision is AnchorComparisonDecision.EQUIVALENT


def test_full_precision_failure_despite_rounded_equality() -> None:
    expected = 1.0448312675151203
    observed = 1.0448322675151203
    rule = AbsoluteToleranceRule(absolute_tolerance=MetricValue(1e-12))
    comparison = compare_anchor_metric(make_reference(value=expected, rule=rule), make_observation(value=observed))
    assert comparison.decision is AnchorComparisonDecision.MATERIAL_DISCREPANCY
    assert abs(expected - observed) > 1e-12
    assert round(expected, 5) == round(observed, 5)
    assert full_precision_failure_stands_despite_rounded_equality(
        full_precision_decision=comparison.decision,
        presentation_decimals=5,
        expected=expected,
        observed=observed,
    )


def test_missing_observation_blocks() -> None:
    comparison = compare_anchor_metric(make_reference(), None)
    assert comparison.decision is AnchorComparisonDecision.BLOCKED_INVALID_INPUT
    assert comparison.reason is AnchorDiscrepancyReason.MISSING_MANDATORY_OBSERVATION


def test_wrong_population_blocks() -> None:
    comparison = compare_anchor_metric(
        make_reference(),
        make_observation(population=PopulationId.CICIOT_FILE_CLIENTS),
    )
    assert comparison.decision is AnchorComparisonDecision.BLOCKED_INVALID_INPUT
    assert comparison.reason is AnchorDiscrepancyReason.WRONG_POPULATION


def test_wrong_threshold_scope_blocks() -> None:
    comparison = compare_anchor_metric(
        make_reference(),
        make_observation(threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD),
    )
    assert comparison.reason is AnchorDiscrepancyReason.WRONG_THRESHOLD_METHOD


def test_wrong_model_identity_blocks() -> None:
    comparison = compare_anchor_metric(
        make_reference(),
        make_observation(training_model=TrainingModelId.FEDPROX_AUTOENCODER),
    )
    assert comparison.reason is AnchorDiscrepancyReason.WRONG_TRAINING_MODEL


def test_wrong_checkpoint_semantics_block() -> None:
    comparison = compare_anchor_metric(
        make_reference(),
        make_observation(checkpoint_status=CheckpointStatus.SELECTED_BY_NON_TEST_RULE),
    )
    assert comparison.reason is AnchorDiscrepancyReason.WRONG_CHECKPOINT_SEMANTICS


def test_relative_comparison_against_zero_is_unavailable() -> None:
    rule = RelativeToleranceRule(relative_tolerance=MetricValue(1e-6))
    comparison = compare_anchor_metric(make_reference(value=0.0, rule=rule), make_observation(value=0.0))
    assert comparison.decision is AnchorComparisonDecision.UNAVAILABLE
    assert comparison.reason is AnchorDiscrepancyReason.RELATIVE_COMPARISON_UNDEFINED_FOR_ZERO_REFERENCE
    assert comparison.relative_difference is None


def test_unsupported_global_tolerance_is_rejected() -> None:
    with pytest.raises(ValueError, match="global floating-point tolerance"):
        reject_global_floating_point_tolerance()


def test_interval_overlap_preserves_interval_semantics() -> None:
    comparison = compare_anchor_metric(
        make_reference(
            rule=IntervalOverlapRule(),
            interval=MetricInterval(lower=MetricValue(0.1), upper=MetricValue(0.3)),
        ),
        make_observation(interval=MetricInterval(lower=MetricValue(0.25), upper=MetricValue(0.4))),
    )
    assert comparison.decision is AnchorComparisonDecision.EQUIVALENT


def test_exact_count_comparison() -> None:
    comparison = compare_anchor_metric(
        make_reference(rule=ExactCountRule(), count=ClientCount(9)),
        make_observation(count=ClientCount(9)),
    )
    assert comparison.decision is AnchorComparisonDecision.EQUIVALENT
