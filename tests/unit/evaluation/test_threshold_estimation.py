from types import SimpleNamespace
from typing import cast

import numpy as np
import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate
from tests.unit.thresholding.helpers import client_scores

from datp_core.analysis.metrics.models import MetricReason, MetricStatus
from datp_core.analysis.metrics.threshold_estimation import (
    ThresholdEstimationDiagnostic,
    ThresholdEstimationProvenance,
    evaluate_threshold_estimate,
    sample_efficiency_curve,
)
from datp_core.analysis.metrics.threshold_evidence import VerifiedHeldOutBenignScores, verify_held_out_benign_scores
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import CalibrationSize, Quantile, ReplicateIndex, ScoreValue, Seed, ThresholdValue
from datp_core.experiments.execution.workspace import _pooled_calibration_quantile
from datp_core.thresholds.quantiles import exact_empirical_quantile


def test_threshold_estimation_rejects_an_empty_held_out_benign_score_set() -> None:
    provenance = ThresholdEstimationProvenance(
        client_identity("client_a"),
        fedavg_coordinate(Seed(5)),
        Seed(5),
        CalibrationSize(10),
        ReplicateIndex(0),
        Quantile(0.9),
    )

    with pytest.raises(ScientificContractError, match="non-empty"):
        verify_held_out_benign_scores(
            client=provenance.client,
            coordinate=provenance.coordinate,
            scores=(),
        )


def test_threshold_estimation_oracle_pools_only_eligible_calibration_scores() -> None:
    scores_a = client_scores("client_a", (0.1, 0.2, 0.3))
    scores_b = client_scores("client_b", (0.4, 0.5))
    calibration_by_client = {scores_a.client: scores_a, scores_b.client: scores_b}
    quantile = Quantile(0.9)
    oracle = _pooled_calibration_quantile(calibration_by_client, quantile)
    pooled_calibration = np.asarray((0.1, 0.2, 0.3, 0.4, 0.5), dtype=np.float64)
    assert oracle == exact_empirical_quantile(pooled_calibration, quantile)

    assert oracle.value != exact_empirical_quantile(np.asarray((99.0, 98.0), dtype=np.float64), quantile).value


def test_sample_efficiency_uses_the_locked_sample_variance() -> None:
    coordinate = fedavg_coordinate(Seed(5))
    diagnostics = tuple(
        cast(
            ThresholdEstimationDiagnostic,
            SimpleNamespace(
                provenance=ThresholdEstimationProvenance(
                    client_identity("client_a"),
                    coordinate,
                    Seed(5),
                    CalibrationSize(50),
                    ReplicateIndex(index),
                    Quantile(0.95),
                ),
                estimated_threshold=ThresholdValue(value),
            ),
        )
        for index, value in enumerate((1.0, 2.0, 3.0))
    )

    point = sample_efficiency_curve(diagnostics)[0]

    assert point.replicate_count.value == 3
    assert point.mean_threshold.value == pytest.approx(2.0)
    assert point.threshold_variance_across_nested_replicates is not None
    assert point.threshold_variance_across_nested_replicates.value == pytest.approx(1.0)
    assert point.threshold_standard_deviation_across_nested_replicates is not None
    assert point.threshold_standard_deviation_across_nested_replicates.value == pytest.approx(1.0)


def test_sample_efficiency_single_replicate_has_undefined_variance() -> None:
    coordinate = fedavg_coordinate(Seed(5))
    diagnostics = (
        cast(
            ThresholdEstimationDiagnostic,
            SimpleNamespace(
                provenance=ThresholdEstimationProvenance(
                    client_identity("client_a"),
                    coordinate,
                    Seed(5),
                    CalibrationSize(50),
                    ReplicateIndex(0),
                    Quantile(0.95),
                ),
                estimated_threshold=ThresholdValue(2.0),
            ),
        ),
    )

    point = sample_efficiency_curve(diagnostics)[0]

    assert point.replicate_count.value == 1
    assert point.mean_threshold.value == pytest.approx(2.0)
    assert point.threshold_variance_across_nested_replicates is None
    assert point.threshold_standard_deviation_across_nested_replicates is None


def test_threshold_estimation_preserves_oracle_error_and_attainment_semantics() -> None:
    coordinate = fedavg_coordinate(Seed(5))
    provenance = ThresholdEstimationProvenance(
        client_identity("client_a"),
        coordinate,
        Seed(5),
        CalibrationSize(10),
        ReplicateIndex(0),
        Quantile(0.8),
    )
    held_out_scores = cast(
        VerifiedHeldOutBenignScores,
        SimpleNamespace(
            client=provenance.client,
            coordinate=coordinate,
            scores=tuple(SimpleNamespace(score=value) for value in (ScoreValue(0.1), ScoreValue(0.5))),
        ),
    )

    diagnostic = evaluate_threshold_estimate(
        provenance=provenance,
        estimated_threshold=ThresholdValue(0.1),
        exact_pooled_benign_quantile_reference=ThresholdValue(0.5),
        verified_benign_scores=held_out_scores,
    )
    metrics = {metric.metric: metric for metric in diagnostic.metrics}

    assert diagnostic.target_exceedance.value == pytest.approx(0.2)
    assert diagnostic.achieved_benign_exceedance.value == pytest.approx(0.5)
    absolute_threshold_error = metrics[MetricId.ABSOLUTE_THRESHOLD_ERROR]
    relative_threshold_error = metrics[MetricId.RELATIVE_THRESHOLD_ERROR]
    assert absolute_threshold_error.value is not None
    assert absolute_threshold_error.value.value == pytest.approx(0.4)
    assert relative_threshold_error.value is not None
    assert relative_threshold_error.value.value == pytest.approx(0.8)
    assert diagnostic.signed_attainment_error.value == pytest.approx(0.3)
    assert diagnostic.absolute_attainment_error.value == pytest.approx(0.3)

    zero_oracle = evaluate_threshold_estimate(
        provenance=provenance,
        estimated_threshold=ThresholdValue(0.1),
        exact_pooled_benign_quantile_reference=ThresholdValue(0.0),
        verified_benign_scores=held_out_scores,
    )
    assert zero_oracle.relative_threshold_error_status is MetricStatus.UNDEFINED
    assert zero_oracle.relative_error_unavailable_reason is MetricReason.ZERO_MEAN
