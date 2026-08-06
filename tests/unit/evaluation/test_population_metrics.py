from tests.unit.learning.federated.helpers import client_identity, fedavg_coordinate

from datp_core.datasets.partitioning.contracts import PopulationOutcomeLabel
from datp_core.domain.enums import EvaluationCohort, EvidenceRole, FederatedThresholdMethod, MetricId
from datp_core.domain.values.checksums import Checksum
from datp_core.domain.values.counts import RowCount, Seed
from datp_core.domain.values.ratios import ScoreValue, ThresholdValue
from datp_core.evaluation.client_metrics import calculate_client_metrics
from datp_core.evaluation.models import ClientMetricResult, ConfusionCounts
from datp_core.evaluation.population_metrics import calculate_population_metrics


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
