import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel
from datp_core.domain.enums import EvaluationCohort, EvidenceRole, FederatedThresholdMethod, MetricId
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RowCount, Seed
from datp_core.domain.values.ratios import ScoreValue, ThresholdValue
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.models import ClientMetricResult, ConfusionCounts
from datp_core.evaluation.population_metrics import calculate_population_metrics


@given(false_positives=st.lists(st.integers(min_value=0, max_value=10), min_size=1, max_size=6))
def test_population_fpr_aggregates_stay_within_the_client_fpr_envelope(false_positives: list[int]) -> None:
    results = tuple(_client_result(index, false_positive) for index, false_positive in enumerate(false_positives))

    population = calculate_population_metrics(results)
    metrics = {metric.metric: metric for metric in population.metrics}
    observed_fprs = tuple(false_positive / 10 for false_positive in false_positives)

    mean_fpr = metrics[MetricId.MEAN_FPR].value
    fpr_range = metrics[MetricId.FPR_RANGE].value
    worst_fpr = metrics[MetricId.WORST_CLIENT_FPR].value
    assert mean_fpr is not None
    assert min(observed_fprs) - 1e-12 <= mean_fpr.value <= max(observed_fprs) + 1e-12
    assert fpr_range is not None
    assert fpr_range.value == pytest.approx(max(observed_fprs) - min(observed_fprs))
    assert worst_fpr is not None
    assert worst_fpr.value == pytest.approx(max(observed_fprs))
    assert population.fpr_evaluable_client_count.value == len(false_positives)


def _client_result(index: int, false_positive: int) -> ClientMetricResult:
    coordinate = fedavg_coordinate(Seed(9))
    client = client_identity(f"client_{index}")
    confusion = ConfusionCounts(
        true_negative=RowCount(10 - false_positive),
        false_positive=RowCount(false_positive),
        true_positive=RowCount(1),
        false_negative=RowCount(0),
        attack_assignment_valid=True,
    )
    benign_scores = tuple(ScoreValue(0.1) for _ in range(10 - false_positive)) + tuple(
        ScoreValue(0.9) for _ in range(false_positive)
    )
    scores = (*benign_scores, ScoreValue(0.8))
    labels = (PopulationOutcomeLabel.BENIGN,) * 10 + (PopulationOutcomeLabel.ATTACK,)
    return ClientMetricResult(
        coordinate=coordinate,
        threshold_method=FederatedThresholdMethod.SHARED_THRESHOLD,
        client=client,
        cohort=EvaluationCohort.FPR_EVALUABLE,
        threshold=ThresholdValue(0.5),
        confusion=confusion,
        metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
        warnings=(),
        evidence_role=EvidenceRole.CONFIRMATORY,
        evaluation_score_checksum=Checksum("a" * 64),
        evaluation_label_checksum=Checksum("b" * 64),
        source_row_checksum=Checksum("c" * 64),
    )
