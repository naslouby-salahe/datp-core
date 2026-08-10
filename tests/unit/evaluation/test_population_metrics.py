import pytest
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.analysis.metrics.models import ClientMetricResult, ConfusionCounts, metric_by_id
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.artifacts.provenance import Checksum
from datp_core.core.identifiers import EvaluationCohort, EvidenceRole, FederatedThresholdMethod, MetricId
from datp_core.core.numeric import RowCount, ScoreValue, Seed, ThresholdValue
from datp_core.data.populations.contracts import PopulationOutcomeLabel


def test_population_metrics_aggregate_auroc_quality_control() -> None:
    confirmatory = _client_result("client_a", EvaluationCohort.FPR_EVALUABLE, 1, 1)

    result = calculate_population_metrics((confirmatory,))
    metrics = {metric.metric: metric for metric in result.metrics}

    auroc = metrics[MetricId.AUROC]
    assert auroc.value is not None
    assert 0.0 < auroc.value.value <= 1.0


def test_population_metrics_aggregate_confirmatory_per_client_metrics() -> None:
    results = (
        _client_result("client_a", EvaluationCohort.FPR_EVALUABLE, 1, 1),
        _client_result("client_b", EvaluationCohort.FPR_EVALUABLE, 3, 2),
    )

    result = calculate_population_metrics(results)
    metrics = {metric.metric: metric for metric in result.metrics}

    for metric_id in (
        MetricId.FALSE_POSITIVE_RATE,
        MetricId.TRUE_POSITIVE_RATE,
        MetricId.BALANCED_ACCURACY,
        MetricId.BINARY_MACRO_F1,
    ):
        client_values = [
            value.value for item in results if (value := metric_by_id(item.metrics, metric_id).value) is not None
        ]
        expected = sum(client_values) / len(client_values)
        observed = metrics[metric_id].value
        assert observed is not None
        assert observed.value == pytest.approx(expected)


def test_population_metrics_exclude_fallback_attack_values_from_fpr_aggregate() -> None:
    confirmatory = _client_result("confirmatory", EvaluationCohort.FPR_EVALUABLE, 1, 1)
    fallback = _client_result("fallback", EvaluationCohort.DEPLOYMENT_FALLBACK, 0, 1)

    result = calculate_population_metrics((confirmatory, fallback))
    metrics = {metric.metric: metric for metric in result.metrics}

    assert result.calibration_eligible_client_count.value == 1
    assert result.attack_evaluable_client_count.value == 1
    assert result.deployment_fallback_count.value == 1
    assert result.unavailable_client_count.value == 0
    mean_fpr = metrics[MetricId.MEAN_FPR].value
    assert mean_fpr is not None
    assert mean_fpr.value == 0.5


def _client_result(
    client_id: str, cohort: EvaluationCohort, false_positive: int, true_positive: int
) -> ClientMetricResult:
    coordinate = fedavg_coordinate(seed=Seed(3))
    client = client_identity(client_id)
    confusion = ConfusionCounts(
        true_negative=RowCount(1),
        false_positive=RowCount(false_positive),
        true_positive=RowCount(true_positive),
        false_negative=RowCount(0),
        attack_assignment_valid=True,
    )
    scores = (ScoreValue(0.1), *(ScoreValue(0.9) for _ in range(false_positive + true_positive)))
    labels = (
        PopulationOutcomeLabel.BENIGN,
        *((PopulationOutcomeLabel.BENIGN,) * false_positive),
        *((PopulationOutcomeLabel.ATTACK,) * true_positive),
    )
    return ClientMetricResult(
        coordinate=coordinate,
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        client=client,
        cohort=cohort,
        threshold=ThresholdValue(0.5),
        confusion=confusion,
        metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
        warnings=(),
        evidence_role=EvidenceRole.CONFIRMATORY,
        evaluation_score_checksum=Checksum("a" * 64),
        evaluation_label_checksum=Checksum("b" * 64),
        source_row_checksum=Checksum("c" * 64),
    )
