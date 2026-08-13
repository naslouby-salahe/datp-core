import pytest

from datp_core.core.numeric import MetricValue, Seed
from datp_core.experiments.threshold_robustness.run import (
    _estimator_scope_sign_counts,
    estimator_scope_contrast,
)


def test_estimator_scope_contrast_retains_both_scope_gains_and_difference() -> None:
    contrast = estimator_scope_contrast(
        seed=Seed(2),
        q95_shared=MetricValue(0.5),
        q95_local=MetricValue(0.3),
        moment_shared=MetricValue(0.7),
        moment_local=MetricValue(0.4),
    )

    assert contrast.q95_scope_gain.value == pytest.approx(0.2)
    assert contrast.moment_scope_gain.value == pytest.approx(0.3)
    assert contrast.estimator_sensitivity.value == pytest.approx(0.1)
    sign_counts = _estimator_scope_sign_counts((contrast,))
    assert tuple(item.positive.value for item in sign_counts) == (1, 1)
