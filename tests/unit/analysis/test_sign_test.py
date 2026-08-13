from types import SimpleNamespace
from typing import cast

import pytest

from datp_core.analysis.contrasts import PairedContrasts
from datp_core.analysis.descriptive import count_paired_differences
from datp_core.analysis.inference.sign_test import ExactPairedSignTestResult, exact_paired_sign_test
from datp_core.analysis.inference.wilcoxon import PValue
from datp_core.core.numeric import MetricValue, PairedObservationCount


def test_exact_paired_sign_test_excludes_zeros_from_the_binomial_null() -> None:
    contrasts = cast(
        PairedContrasts,
        SimpleNamespace(deltas=(MetricValue(1.0), MetricValue(0.0), MetricValue(-1.0), MetricValue(2.0))),
    )

    result = exact_paired_sign_test(contrasts)

    assert result.positive_pair_count.value == 2
    assert result.negative_pair_count.value == 1
    assert result.nonzero_pair_count.value == 3
    assert result.two_sided_p_value is not None
    assert result.two_sided_p_value.value == pytest.approx(1.0)
    proportion = count_paired_differences(contrasts.deltas).positive_proportion
    assert proportion is not None
    assert proportion.value == pytest.approx(0.5)


def test_exact_paired_sign_test_rejects_an_impossible_availability_state() -> None:
    with pytest.raises(ValueError, match="p-value"):
        ExactPairedSignTestResult(
            positive_pair_count=PairedObservationCount(0),
            negative_pair_count=PairedObservationCount(1),
            nonzero_pair_count=PairedObservationCount(1),
            two_sided_p_value=None,
        )

    with pytest.raises(ValueError, match="cannot exceed"):
        ExactPairedSignTestResult(
            positive_pair_count=PairedObservationCount(2),
            negative_pair_count=PairedObservationCount(0),
            nonzero_pair_count=PairedObservationCount(1),
            two_sided_p_value=PValue(1.0),
        )


def test_exact_paired_sign_test_retains_the_locked_ten_positive_pair_p_value() -> None:
    contrasts = cast(
        PairedContrasts,
        SimpleNamespace(deltas=(MetricValue(1.0),) * 10),
    )

    result = exact_paired_sign_test(contrasts)

    assert result.positive_pair_count == PairedObservationCount(10)
    assert result.negative_pair_count == PairedObservationCount(0)
    assert result.two_sided_p_value == PValue(0.001953125)


def test_exact_paired_sign_test_is_unavailable_when_every_delta_is_zero() -> None:
    contrasts = cast(
        PairedContrasts,
        SimpleNamespace(deltas=(MetricValue(0.0), MetricValue(0.0))),
    )

    result = exact_paired_sign_test(contrasts)

    assert result.nonzero_pair_count == PairedObservationCount(0)
    assert result.two_sided_p_value is None
