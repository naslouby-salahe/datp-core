from types import SimpleNamespace
from typing import cast

import pytest
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.analysis.inference.bootstrap.contracts import BcaOutcome
from datp_core.analysis.mechanisms.equity_pareto import equity_utility_pareto
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import AvailableMetric
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import ExperimentId, FederatedThresholdMethod, FigureTitle, MetricId
from datp_core.core.numeric import MetricValue, Seed
from datp_core.experiments.confirmatory.run import _declaration_for_threshold_method
from datp_core.presentation.figures import equity_utility_pareto_figure


def test_equity_pareto_uses_mean_coordinates_and_does_not_scalarize() -> None:
    documents = (
        _document(FederatedThresholdMethod.SHARED_THRESHOLD, Seed(0), 0.2, 0.7),
        _document(FederatedThresholdMethod.SHARED_THRESHOLD, Seed(1), 0.4, 0.9),
        _document(FederatedThresholdMethod.LOCAL_THRESHOLD, Seed(0), 0.2, 0.8),
        _document(FederatedThresholdMethod.LOCAL_THRESHOLD, Seed(1), 0.3, 0.8),
        _document(FederatedThresholdMethod.CLUSTER_THRESHOLD, Seed(0), 0.1, 0.5),
        _document(FederatedThresholdMethod.CLUSTER_THRESHOLD, Seed(1), 0.2, 0.6),
    )

    result = equity_utility_pareto(documents, utility_metric=MetricId.P10_BINARY_MACRO_F1)

    assert [(point.threshold_method, point.nondominated) for point in result.points] == [
        (FederatedThresholdMethod.CLUSTER_THRESHOLD, True),
        (FederatedThresholdMethod.LOCAL_THRESHOLD, True),
        (FederatedThresholdMethod.SHARED_THRESHOLD, False),
    ]
    shared = next(
        row for row in result.target_attainment if row.threshold_method is FederatedThresholdMethod.SHARED_THRESHOLD
    )
    assert shared.mean_absolute_target_error.value == pytest.approx(0.15)
    assert shared.worst_absolute_target_error.value == pytest.approx(0.3)
    assert shared.mean_absolute_calibration_generalization_gap.value == pytest.approx(0.075)


def test_equity_pareto_rejects_methods_with_different_seed_cohorts() -> None:
    documents = (
        _document(FederatedThresholdMethod.SHARED_THRESHOLD, Seed(0), 0.2, 0.7),
        _document(FederatedThresholdMethod.LOCAL_THRESHOLD, Seed(1), 0.2, 0.8),
    )

    with pytest.raises(ScientificContractError, match="common seed cohort"):
        equity_utility_pareto(documents, utility_metric=MetricId.P10_BINARY_MACRO_F1)


def test_equity_pareto_exposes_descriptive_bca_intervals_for_full_seed_cohort() -> None:
    documents = tuple(
        _document(
            FederatedThresholdMethod.SHARED_THRESHOLD,
            Seed(seed),
            0.1 + seed / 100,
            0.6 + seed / 100,
        )
        for seed in range(10)
    )

    result = equity_utility_pareto(documents, utility_metric=MetricId.P10_BINARY_MACRO_F1)

    assert result.points[0].x_interval.outcome is BcaOutcome.AVAILABLE
    assert result.points[0].y_interval.outcome is BcaOutcome.AVAILABLE
    figure = equity_utility_pareto_figure(result, title=FigureTitle("Equity utility"))
    assert len(figure.paired_metric_series) == 2
    assert figure.paired_metric_series[0].x_values == (result.points[0].mean_x,)
    assert figure.paired_metric_series[1].x_values == result.points[0].seed_values_x


@pytest.mark.parametrize(
    ("method", "experiment"),
    (
        (FederatedThresholdMethod.POOLED_SHARED_QUANTILE, ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY),
        (FederatedThresholdMethod.SAMPLE_WEIGHTED_SHARED_THRESHOLD, ExperimentId.SHARED_CONSTRUCTION_SENSITIVITY),
        (FederatedThresholdMethod.FEDERATED_KLL_SHARED_THRESHOLD, ExperimentId.FEDERATED_QUANTILE_ESTIMATION),
        (FederatedThresholdMethod.FEDERATED_BENIGN_STATISTICS, ExperimentId.FEDERATED_QUANTILE_ESTIMATION),
    ),
)
def test_pareto_policy_coordinates_use_their_declared_canonical_experiment(
    method: FederatedThresholdMethod, experiment: ExperimentId
) -> None:
    assert _declaration_for_threshold_method(method).id is experiment


def _document(
    method: FederatedThresholdMethod, seed: Seed, cv_fpr: float, utility: float
) -> FederatedEvaluationDocument:
    coordinate = fedavg_coordinate(seed)
    metrics = (
        AvailableMetric(MetricId.FPR_COEFFICIENT_OF_VARIATION, MetricValue(cv_fpr)),
        AvailableMetric(MetricId.P10_BINARY_MACRO_F1, MetricValue(utility)),
    )
    return cast(
        FederatedEvaluationDocument,
        SimpleNamespace(
            threshold_method=method,
            score_coordinate=coordinate,
            population=SimpleNamespace(metrics=metrics),
            diagnostics=SimpleNamespace(
                held_out_operating_point_summary=SimpleNamespace(
                    mean_absolute_target_error=MetricValue(0.1 + seed.value * 0.1),
                    worst_absolute_target_error=MetricValue(0.2 + seed.value * 0.2),
                    mean_absolute_calibration_generalization_gap=MetricValue(0.05 + seed.value * 0.05),
                )
            ),
        ),
    )
