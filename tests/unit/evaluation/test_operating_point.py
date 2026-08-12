from types import SimpleNamespace
from typing import cast

import pytest
from tests.unit.thresholding.helpers import client_scores, identity

from datp_core.analysis.metrics.models import AvailableMetric, ClientMetricResult
from datp_core.analysis.metrics.operating_point import calibration_support_evidence, evaluate_held_out_operating_points
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import MetricValue, Quantile, ThresholdValue


def test_held_out_operating_point_uses_strict_calibration_exceedance() -> None:
    client = identity("client_0")
    result = cast(
        ClientMetricResult,
        SimpleNamespace(
            client=client,
            threshold=ThresholdValue(1.0),
            metrics=(AvailableMetric(MetricId.FALSE_POSITIVE_RATE, MetricValue(0.5)),),
        ),
    )

    diagnostics, summary = evaluate_held_out_operating_points(
        (result,),
        (client_scores("client_0", (0.5, 1.0, 2.0)),),
        Quantile(0.95),
    )

    assert diagnostics[0].calibration_exceedance.value == 1.0 / 3.0
    assert diagnostics[0].signed_calibration_target_error.value == pytest.approx(1.0 / 3.0 - 0.05)
    assert diagnostics[0].held_out_false_positive_rate.value == 0.5
    assert diagnostics[0].signed_target_error.value == pytest.approx(0.45)
    assert diagnostics[0].signed_calibration_generalization_gap.value == pytest.approx(1.0 / 6.0)
    assert summary is not None
    assert summary.worst_absolute_target_error.value == pytest.approx(0.45)


def test_calibration_support_evidence_persists_each_client_source_count() -> None:
    evidence = calibration_support_evidence((client_scores("client_0", (0.5, 1.0, 2.0)),))

    assert evidence[0].source_benign_calibration_count.value == 3
