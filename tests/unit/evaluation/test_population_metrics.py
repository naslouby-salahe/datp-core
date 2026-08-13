from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.analysis.metrics.models import ClientMetricResult, ConfusionCounts, metric_by_id
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.core.identifiers import (
    ClientIdentityToken,
    EvaluationCohort,
    EvidenceRole,
    FederatedThresholdMethod,
    MetricId,
    PopulationId,
    PopulationIdentityKind,
    PreprocessingProtocolId,
    SplitProtocolId,
    TrainingModelId,
)
from datp_core.core.numeric import MetricValue, RowCount, ScoreValue, Seed, ThresholdValue
from datp_core.data.populations.contracts import ClientIdentity, PopulationOutcomeLabel
from datp_core.detector.training.contracts import FederatedTrainingCoordinate

_COORDINATE = FederatedTrainingCoordinate(
    population=PopulationId.NBAIOT_NATURAL_DEVICES,
    training_seed=Seed(0),
    split_protocol=SplitProtocolId.NON_TEMPORAL_EQUAL_THIRDS,
    preprocessing_identity=PreprocessingProtocolId.FEDERATED_CLIENT_LOCAL_STANDARD,
    model=TrainingModelId.FEDAVG_AUTOENCODER,
    model_coefficient=None,
)


def _client_result(
    *,
    client_id: str,
    cohort: EvaluationCohort,
    confusion: ConfusionCounts,
    scores: tuple[ScoreValue, ...],
    labels: tuple[PopulationOutcomeLabel, ...],
) -> ClientMetricResult:
    return ClientMetricResult(
        coordinate=_COORDINATE,
        threshold_method=FederatedThresholdMethod.LOCAL_THRESHOLD,
        client=ClientIdentity(
            PopulationId.NBAIOT_NATURAL_DEVICES,
            ClientIdentityToken(client_id),
            PopulationIdentityKind.PHYSICAL_DEVICES,
        ),
        cohort=cohort,
        threshold=ThresholdValue(0.5),
        confusion=confusion,
        metrics=calculate_client_metrics(confusion=confusion, scores=scores, labels=labels),
        warnings=(),
        evidence_role=EvidenceRole.CONFIRMATORY,
    )


def test_attack_aggregates_use_attack_evaluable_clients_not_fpr_cohort() -> None:
    fpr_evaluable = _client_result(
        client_id="fpr-client",
        cohort=EvaluationCohort.FPR_EVALUABLE,
        confusion=ConfusionCounts(
            true_negative=RowCount(9),
            false_positive=RowCount(1),
            true_positive=RowCount(0),
            false_negative=RowCount(0),
            attack_assignment_valid=False,
        ),
        scores=(ScoreValue(0.1),) * 10,
        labels=(PopulationOutcomeLabel.BENIGN,) * 10,
    )
    attack_evaluable = _client_result(
        client_id="attack-client",
        cohort=EvaluationCohort.UNAVAILABLE,
        confusion=ConfusionCounts(
            true_negative=RowCount(0),
            false_positive=RowCount(0),
            true_positive=RowCount(1),
            false_negative=RowCount(0),
            attack_assignment_valid=True,
        ),
        scores=(ScoreValue(0.9),),
        labels=(PopulationOutcomeLabel.ATTACK,),
    )

    result = calculate_population_metrics((fpr_evaluable, attack_evaluable))

    average_precision = metric_by_id(result.metrics, MetricId.AVERAGE_PRECISION)
    pooled_macro_f1 = metric_by_id(result.metrics, MetricId.POOLED_MACRO_F1)
    assert average_precision.value == MetricValue(1.0)
    assert average_precision.denominator == RowCount(1)
    assert pooled_macro_f1.denominator == RowCount(1)
    assert result.fpr_evaluable_client_count == RowCount(1)
    assert result.attack_evaluable_client_count == RowCount(1)
