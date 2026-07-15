from decimal import Decimal

import pytest

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.mathematics.dispersion import (
    ClientMoment,
    DefinedCvFpr,
    UndefinedCvFpr,
    cv_fpr,
    pooled_variance,
)
from datp_core.domain.mathematics.pooled_statistics import (
    has_minimum_eligible_calibration_count,
    is_canonical_k,
)
from datp_core.domain.mathematics.quantiles import exact_quantile, exact_weighted_quantile, fpr_target
from datp_core.domain.thresholding.policies import ThresholdPercentile


def test_cv_fpr_matches_the_locked_population_standard_deviation_definition() -> None:
    outcome = cv_fpr(eligible_fprs=(0.1, 0.2, 0.3))

    assert isinstance(outcome, DefinedCvFpr)
    assert outcome.value == pytest.approx((1 / 6) ** 0.5)
    assert isinstance(cv_fpr(eligible_fprs=(0.0, 0.0)), UndefinedCvFpr)


def test_pooled_variance_includes_the_between_client_mean_shift_term() -> None:
    moments = (
        ClientMoment(sample_count=2, mean=1.0, variance=1.0),
        ClientMoment(sample_count=2, mean=5.0, variance=1.0),
    )

    assert pooled_variance(client_moments=moments) == pytest.approx(5.0)


def test_fpr_target_and_exact_quantile_helpers_are_locked() -> None:
    percentile = ThresholdPercentile(value=Decimal("0.75"))

    assert fpr_target(percentile=percentile).value == Decimal("0.250000000000")
    assert exact_quantile(values=(4.0, 1.0, 3.0, 2.0), percentile=percentile) == 3.0
    assert exact_weighted_quantile(values=(1.0, 10.0), weights=(3, 1), percentile=percentile) == 1.0


def test_canonical_k_and_eligibility_helpers_have_no_configuration_surface() -> None:
    assert is_canonical_k(cluster_count=3)
    assert not is_canonical_k(cluster_count=2)
    assert has_minimum_eligible_calibration_count(calibration_count=100, minimum_count=100)
    assert not has_minimum_eligible_calibration_count(calibration_count=99, minimum_count=100)
    with pytest.raises(DomainValidationError):
        has_minimum_eligible_calibration_count(calibration_count=-1, minimum_count=100)
