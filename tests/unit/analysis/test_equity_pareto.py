from types import SimpleNamespace
from typing import cast

import pytest
from tests.unit.learning.federated.helpers import fedavg_coordinate

from datp_core.analysis.mechanisms.equity_pareto import equity_utility_pareto
from datp_core.analysis.metrics.federated import FederatedEvaluationDocument
from datp_core.analysis.metrics.models import AvailableMetric
from datp_core.core.errors import ScientificContractError
from datp_core.core.identifiers import FederatedThresholdMethod, MetricId
from datp_core.core.numeric import MetricValue, Seed


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


def test_equity_pareto_rejects_methods_with_different_seed_cohorts() -> None:
    documents = (
        _document(FederatedThresholdMethod.SHARED_THRESHOLD, Seed(0), 0.2, 0.7),
        _document(FederatedThresholdMethod.LOCAL_THRESHOLD, Seed(1), 0.2, 0.8),
    )

    with pytest.raises(ScientificContractError, match="common seed cohort"):
        equity_utility_pareto(documents, utility_metric=MetricId.P10_BINARY_MACRO_F1)


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
        ),
    )
