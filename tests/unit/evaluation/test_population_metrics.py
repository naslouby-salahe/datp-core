from dataclasses import replace

import pytest

from datp_core.analysis.metrics.client import calculate_client_metrics
from datp_core.analysis.metrics.cohorts import ClientEligibilityRecord, EvaluationCohortManifest
from datp_core.analysis.metrics.models import (
    ClientMetricResult,
    ConfusionCounts,
    MetricReason,
    MetricStatus,
    metric_by_id,
)
from datp_core.analysis.metrics.population import calculate_population_metrics
from datp_core.core.errors import ScientificContractError
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
from datp_core.thresholds.protocols import MINIMUM_BENIGN_SUPPORT

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


def _cohort_for(*results: ClientMetricResult) -> EvaluationCohortManifest:
    return EvaluationCohortManifest(
        population=PopulationId.NBAIOT_NATURAL_DEVICES,
        partition_seed=Seed(0),
        minimum_benign_calibration_support=MINIMUM_BENIGN_SUPPORT,
        records=tuple(
            ClientEligibilityRecord(
                client=result.client,
                benign_calibration_count=RowCount(5000),
                benign_evaluation_count=RowCount(10),
                attack_evaluation_count=RowCount(1 if result.confusion.attack_assignment_valid else 0),
                calibration_eligible=result.cohort is EvaluationCohort.FPR_EVALUABLE,
                fpr_evaluable=result.cohort is EvaluationCohort.FPR_EVALUABLE,
                attack_evaluable=result.confusion.attack_assignment_valid,
                deployment_fallback=result.cohort is EvaluationCohort.DEPLOYMENT_FALLBACK,
                exclusion_reasons=(),
            )
            for result in results
        ),
        memberships=(),
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


def test_cross_client_fpr_aggregates_use_sample_standard_deviation_and_type7_quantiles() -> None:
    results = tuple(
        _client_result(
            client_id=f"fpr-{false_positive}",
            cohort=EvaluationCohort.FPR_EVALUABLE,
            confusion=ConfusionCounts(
                true_negative=RowCount(10 - false_positive),
                false_positive=RowCount(false_positive),
                true_positive=RowCount(0),
                false_negative=RowCount(0),
                attack_assignment_valid=False,
            ),
            scores=(ScoreValue(0.1),) * 10,
            labels=(PopulationOutcomeLabel.BENIGN,) * 10,
        )
        for false_positive in (1, 2, 3)
    )

    aggregates = {item.metric: item for item in calculate_population_metrics(results).metrics}

    for metric, expected in (
        (MetricId.MEAN_FPR, 0.2),
        (MetricId.FPR_SAMPLE_STANDARD_DEVIATION, 0.1),
        (MetricId.FPR_COEFFICIENT_OF_VARIATION, 0.5),
        (MetricId.FPR_IQR, 0.1),
        (MetricId.FPR_RANGE, 0.2),
        (MetricId.WORST_CLIENT_FPR, 0.3),
        (MetricId.JAIN_FAIRNESS_INDEX, 6.0 / 7.0),
        (MetricId.GINI_COEFFICIENT, 2.0 / 9.0),
    ):
        aggregate = aggregates[metric]
        assert aggregate.value is not None
        assert aggregate.value.value == pytest.approx(expected)


def test_cross_client_fpr_cv_has_locked_zero_and_insufficient_support_semantics() -> None:
    one_client = _client_result(
        client_id="single",
        cohort=EvaluationCohort.FPR_EVALUABLE,
        confusion=ConfusionCounts(
            true_negative=RowCount(10),
            false_positive=RowCount(0),
            true_positive=RowCount(0),
            false_negative=RowCount(0),
            attack_assignment_valid=False,
        ),
        scores=(ScoreValue(0.1),) * 10,
        labels=(PopulationOutcomeLabel.BENIGN,) * 10,
    )
    single = {item.metric: item for item in calculate_population_metrics((one_client,)).metrics}
    assert single[MetricId.FPR_SAMPLE_STANDARD_DEVIATION].status is MetricStatus.UNAVAILABLE
    assert single[MetricId.FPR_SAMPLE_STANDARD_DEVIATION].reason is MetricReason.INSUFFICIENT_CLIENT_COUNT
    assert single[MetricId.FPR_COEFFICIENT_OF_VARIATION].status is MetricStatus.UNAVAILABLE
    assert single[MetricId.FPR_COEFFICIENT_OF_VARIATION].reason is MetricReason.INSUFFICIENT_CLIENT_COUNT

    second_zero_client = replace(
        one_client,
        client=ClientIdentity(
            PopulationId.NBAIOT_NATURAL_DEVICES,
            ClientIdentityToken("zero"),
            PopulationIdentityKind.PHYSICAL_DEVICES,
        ),
    )
    zero_mean = {item.metric: item for item in calculate_population_metrics((one_client, second_zero_client)).metrics}
    assert zero_mean[MetricId.FPR_COEFFICIENT_OF_VARIATION].status is MetricStatus.UNDEFINED
    assert zero_mean[MetricId.FPR_COEFFICIENT_OF_VARIATION].reason is MetricReason.ZERO_MEAN


def test_cross_client_attack_aggregates_use_attack_evaluable_client_cohort() -> None:
    perfect = _client_result(
        client_id="perfect",
        cohort=EvaluationCohort.FPR_EVALUABLE,
        confusion=ConfusionCounts(
            true_negative=RowCount(1),
            false_positive=RowCount(0),
            true_positive=RowCount(1),
            false_negative=RowCount(0),
            attack_assignment_valid=True,
        ),
        scores=(ScoreValue(0.1), ScoreValue(0.9)),
        labels=(PopulationOutcomeLabel.BENIGN, PopulationOutcomeLabel.ATTACK),
    )
    mixed = _client_result(
        client_id="mixed",
        cohort=EvaluationCohort.FPR_EVALUABLE,
        confusion=ConfusionCounts(
            true_negative=RowCount(1),
            false_positive=RowCount(1),
            true_positive=RowCount(1),
            false_negative=RowCount(1),
            attack_assignment_valid=True,
        ),
        scores=(ScoreValue(0.9), ScoreValue(0.9), ScoreValue(0.1), ScoreValue(0.1)),
        labels=(
            PopulationOutcomeLabel.BENIGN,
            PopulationOutcomeLabel.ATTACK,
            PopulationOutcomeLabel.BENIGN,
            PopulationOutcomeLabel.ATTACK,
        ),
    )

    aggregates = {item.metric: item for item in calculate_population_metrics((perfect, mixed)).metrics}

    for metric, expected in (
        (MetricId.TPR_COEFFICIENT_OF_VARIATION, 0.47140452079103173),
        (MetricId.P10_BINARY_MACRO_F1, 0.55),
        (MetricId.WORST_CLIENT_BALANCED_ACCURACY, 0.5),
        (MetricId.MEAN_CLIENT_MACRO_F1, 0.75),
        (MetricId.MEAN_CLIENT_BALANCED_ACCURACY, 0.75),
    ):
        aggregate = aggregates[metric]
        assert aggregate.value is not None
        assert aggregate.value.value == pytest.approx(expected)
        assert aggregate.denominator == RowCount(2)


def test_population_aggregates_reject_a_manifest_that_omits_evaluated_clients() -> None:
    first = _client_result(
        client_id="first",
        cohort=EvaluationCohort.FPR_EVALUABLE,
        confusion=ConfusionCounts(RowCount(9), RowCount(1), RowCount(0), RowCount(0), False),
        scores=(ScoreValue(0.1),) * 10,
        labels=(PopulationOutcomeLabel.BENIGN,) * 10,
    )
    second = replace(
        first,
        client=ClientIdentity(
            PopulationId.NBAIOT_NATURAL_DEVICES,
            ClientIdentityToken("second"),
            PopulationIdentityKind.PHYSICAL_DEVICES,
        ),
    )

    with pytest.raises(ScientificContractError, match="exactly the declared cohort clients"):
        calculate_population_metrics((first, second), cohort=_cohort_for(first))


def test_population_aggregates_reject_attack_evidence_not_declared_by_cohort() -> None:
    result = _client_result(
        client_id="attack",
        cohort=EvaluationCohort.UNAVAILABLE,
        confusion=ConfusionCounts(RowCount(0), RowCount(0), RowCount(1), RowCount(0), True),
        scores=(ScoreValue(0.9),),
        labels=(PopulationOutcomeLabel.ATTACK,),
    )
    invalid_manifest = _cohort_for(result).model_copy(
        update={
            "records": (
                ClientEligibilityRecord(
                    client=result.client,
                    benign_calibration_count=RowCount(5000),
                    benign_evaluation_count=RowCount(10),
                    attack_evaluation_count=RowCount(0),
                    calibration_eligible=False,
                    fpr_evaluable=False,
                    attack_evaluable=False,
                    deployment_fallback=False,
                    exclusion_reasons=(),
                ),
            )
        }
    )

    with pytest.raises(ScientificContractError, match="attack validity conflicts"):
        calculate_population_metrics((result,), cohort=invalid_manifest)
