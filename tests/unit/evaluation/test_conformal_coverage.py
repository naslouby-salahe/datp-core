from tests.unit.learning.federated.helpers import (
    client_identity,
    fedavg_coordinate,
)

from datp_core.analysis.metrics.conformal import (
    evaluate_held_out_conformal_coverage,
)
from datp_core.analysis.metrics.models import MetricReason, MetricStatus, metric_by_id
from datp_core.core.identifiers import MetricId
from datp_core.core.numeric import (
    ConformalRankIndex,
    CoverageTarget,
    Quantile,
    RowCount,
    ScoreValue,
    Seed,
    ThresholdValue,
)
from datp_core.thresholds.variants.conformal import ConformalAssignment


def test_conformal_coverage_empty_held_out_benign_scores_is_typed_unavailable() -> None:
    coordinate = fedavg_coordinate(Seed(4))
    assignment = ConformalAssignment(
        client=client_identity("client_a"),
        calibration_count=RowCount(10),
        rank_index=ConformalRankIndex(9),
        effective_quantile=Quantile(0.9),
        selected_score=ScoreValue(0.5),
        tie_count=RowCount(0),
        threshold=ThresholdValue(0.5),
    )
    result = evaluate_held_out_conformal_coverage(
        assignment,
        coordinate,
        Seed(4),
        CoverageTarget(0.9),
        (),
    )
    achieved = metric_by_id(result.metrics, MetricId.ACHIEVED_COVERAGE)
    target = metric_by_id(result.metrics, MetricId.TARGET_COVERAGE)
    assert result.unavailable_reason is MetricReason.EMPTY_BENIGN_DENOMINATOR
    assert achieved.status is MetricStatus.UNAVAILABLE
    assert target.metric is MetricId.TARGET_COVERAGE
