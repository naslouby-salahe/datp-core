"""Roadmap-exact operating-point metric behavior."""

import pytest

from datp_core.domain.evaluation import (
    ClientConfusionMatrix,
    MetricStatus,
    assert_auroc_invariant,
    calculate_fpr_dispersion,
)
from datp_core.domain.identifiers import ClientId


def test_missing_class_metrics_are_explicitly_unavailable() -> None:
    matrix = ClientConfusionMatrix(
        client_id=ClientId("client"), true_positives=0, false_positives=0, true_negatives=0, false_negatives=0
    )

    assert matrix.false_positive_rate.value is None
    assert matrix.false_positive_rate.status is MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS
    assert matrix.true_positive_rate.status is MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS
    assert matrix.balanced_accuracy.value is None
    assert matrix.macro_f1.value is None


def test_cross_client_fpr_dispersion_uses_population_standard_deviation() -> None:
    result = calculate_fpr_dispersion((0.1, 0.2, 0.3), cv_instability_threshold=0.01, quantile_method="linear")

    assert result.mean_fpr.value == pytest.approx(0.2)
    assert result.standard_deviation.value == pytest.approx((2 / 300) ** 0.5)
    assert result.coefficient_of_variation.value == pytest.approx(((2 / 300) ** 0.5) / 0.2)
    assert result.iqr.value == pytest.approx(0.1)
    assert result.value_range.value == pytest.approx(0.2)


def test_zero_mean_fpr_cv_is_undefined_without_epsilon_stabilization() -> None:
    result = calculate_fpr_dispersion((0.0, 0.0), cv_instability_threshold=0.01, quantile_method="linear")

    assert result.coefficient_of_variation.value is None
    assert result.coefficient_of_variation.status is MetricStatus.UNDEFINED_ZERO_DENOMINATOR


def test_near_zero_fpr_keeps_numeric_cv_with_an_explicit_warning_status() -> None:
    result = calculate_fpr_dispersion((0.001, 0.003), cv_instability_threshold=0.01, quantile_method="linear")

    assert result.coefficient_of_variation.value is not None
    assert result.coefficient_of_variation.status is MetricStatus.UNDEFINED_NEAR_ZERO_DENOMINATOR


def test_auroc_invariance_rejects_policy_drift() -> None:
    assert_auroc_invariant((0.7, 0.7), tolerance=1e-12)
    with pytest.raises(ValueError, match="invariant"):
        assert_auroc_invariant((0.7, 0.71), tolerance=1e-12)
