from tests.unit.anchor.helpers import matching_anchor_observations

from datp_core.analysis.inference.bootstrap.contracts import BcaAdjustment, BcaOutcome, BcaReason, BootstrapInterval
from datp_core.core.numeric import MetricValue, Seed
from datp_core.experiments.anchor.contracts import AnchorComparisonDecision, AnchorDiscrepancyReason
from datp_core.experiments.anchor.reproduction import _anchor_bca_comparison, _classify_bca_comparison
from datp_core.experiments.anchor.spec import (
    ANCHOR_INFERENCE_PROTOCOL,
    ANCHOR_MAXIMUM_OPERATIVE_WIDTH,
    ANCHOR_REFERENCE_INTERVAL,
    HISTORICAL_ANCHOR_SEED_COHORT,
)

_ANALYSIS_SEED = Seed(3)


def _available_interval(*, lower: float, upper: float) -> BootstrapInterval:
    return BootstrapInterval.available(
        protocol=ANCHOR_INFERENCE_PROTOCOL,
        analysis_seed=_ANALYSIS_SEED,
        point_estimate=MetricValue((lower + upper) / 2.0),
        lower_bound=MetricValue(lower),
        upper_bound=MetricValue(upper),
        adjustment=BcaAdjustment(bias_correction=MetricValue(0.0), acceleration=MetricValue(0.0)),
    )


def test_locked_reference_bounds_are_exact() -> None:
    assert ANCHOR_REFERENCE_INTERVAL.lower.value == 0.647
    assert ANCHOR_REFERENCE_INTERVAL.upper.value == 0.769
    assert ANCHOR_MAXIMUM_OPERATIVE_WIDTH.value == 0.1464


def test_matching_historical_observations_reproduce_an_equivalent_bca_interval() -> None:
    comparison = _anchor_bca_comparison(matching_anchor_observations(), HISTORICAL_ANCHOR_SEED_COHORT)
    assert comparison.interval.outcome is BcaOutcome.AVAILABLE
    assert comparison.decision is AnchorComparisonDecision.EQUIVALENT
    assert comparison.reason is None
    assert comparison.interval.lower_bound is not None
    assert comparison.interval.lower_bound.value > 0.0


def test_exact_maximum_width_passes() -> None:
    interval = _available_interval(lower=0.6, upper=0.6 + 0.1464)
    comparison = _classify_bca_comparison(interval)
    assert comparison.decision is AnchorComparisonDecision.EQUIVALENT
    assert comparison.reason is None


def test_width_just_above_maximum_fails() -> None:
    interval = _available_interval(lower=0.6, upper=0.6 + 0.1464 + 1e-9)
    comparison = _classify_bca_comparison(interval)
    assert comparison.decision is AnchorComparisonDecision.MATERIAL_DISCREPANCY
    assert comparison.reason is AnchorDiscrepancyReason.BCA_INTERVAL_WIDTH_EXCEEDS_MAXIMUM


def test_non_positive_lower_bound_fails_even_when_narrow_and_overlapping() -> None:
    interval = _available_interval(lower=0.0, upper=0.1)
    comparison = _classify_bca_comparison(interval)
    assert comparison.decision is AnchorComparisonDecision.MATERIAL_DISCREPANCY
    assert comparison.reason is AnchorDiscrepancyReason.BCA_INTERVAL_NOT_ENTIRELY_POSITIVE


def test_negative_lower_bound_fails() -> None:
    interval = _available_interval(lower=-0.01, upper=0.1)
    comparison = _classify_bca_comparison(interval)
    assert comparison.reason is AnchorDiscrepancyReason.BCA_INTERVAL_NOT_ENTIRELY_POSITIVE


def test_positive_but_non_overlapping_interval_fails() -> None:
    interval = _available_interval(lower=0.05, upper=0.2)
    comparison = _classify_bca_comparison(interval)
    assert comparison.decision is AnchorComparisonDecision.MATERIAL_DISCREPANCY
    assert comparison.reason is AnchorDiscrepancyReason.BCA_INTERVAL_DOES_NOT_OVERLAP_REFERENCE


def test_interval_touching_reference_boundary_counts_as_overlap() -> None:
    interval = _available_interval(lower=0.6, upper=0.647)
    comparison = _classify_bca_comparison(interval)
    assert comparison.decision is AnchorComparisonDecision.EQUIVALENT


def test_unavailable_bca_interval_blocks_the_gate() -> None:
    blocked = BootstrapInterval.blocked(
        protocol=ANCHOR_INFERENCE_PROTOCOL,
        analysis_seed=_ANALYSIS_SEED,
        point_estimate=None,
        reason=BcaReason.SEED_COHORT_MISMATCH,
    )
    comparison = _classify_bca_comparison(blocked)
    assert comparison.decision is AnchorComparisonDecision.UNAVAILABLE
    assert comparison.reason is AnchorDiscrepancyReason.BCA_INTERVAL_UNAVAILABLE

    degenerate = BootstrapInterval.degenerate(
        protocol=ANCHOR_INFERENCE_PROTOCOL,
        analysis_seed=_ANALYSIS_SEED,
        point_estimate=MetricValue(0.1),
        reason=BcaReason.DEGENERATE_BOOTSTRAP_DISTRIBUTION,
    )
    comparison = _classify_bca_comparison(degenerate)
    assert comparison.decision is AnchorComparisonDecision.UNAVAILABLE
    assert comparison.reason is AnchorDiscrepancyReason.BCA_INTERVAL_UNAVAILABLE


def test_incomplete_seed_coverage_is_treated_as_unavailable() -> None:
    partial_observations = tuple(
        item for item in matching_anchor_observations() if item.seed != HISTORICAL_ANCHOR_SEED_COHORT.values[0]
    )
    comparison = _anchor_bca_comparison(partial_observations, HISTORICAL_ANCHOR_SEED_COHORT)
    assert comparison.decision is AnchorComparisonDecision.UNAVAILABLE
    assert comparison.reason is AnchorDiscrepancyReason.BCA_INTERVAL_UNAVAILABLE
