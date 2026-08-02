from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.domain.enums import MetricId
from datp_core.domain.values import CoverageTarget, Quantile, RowCount, ScoreValue, Seed, ThresholdValue
from datp_core.evaluation.conformal_coverage import CoverageUnavailableReason, evaluate_held_out_conformal_coverage
from datp_core.evaluation.models import MetricStatus
from datp_core.thresholding.models import ConformalAssignment


def test_conformal_coverage_empty_held_out_benign_scores_is_typed_unavailable() -> None:
    coordinate = fedavg_coordinate(Seed(4))
    client = client_identity("client_a")
    assignment = ConformalAssignment(
        client, RowCount(10), 9, Quantile(0.9), ScoreValue(0.5), RowCount(0), ThresholdValue(0.5)
    )

    result = evaluate_held_out_conformal_coverage(assignment, coordinate, Seed(4), CoverageTarget(0.9), ())

    assert result.unavailable_reason is CoverageUnavailableReason.NO_HELD_OUT_BENIGN_SCORES
    assert result.result.achieved_held_out_benign_coverage.status is MetricStatus.UNAVAILABLE
    assert result.result.target_coverage.metric is MetricId.TARGET_COVERAGE
