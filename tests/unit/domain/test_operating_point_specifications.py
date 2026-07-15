from collections.abc import Callable
from decimal import Decimal

import pytest

from datp_core.domain.artifacts.references import CalibrationScoreArtifactId, StageFingerprint
from datp_core.domain.errors import DomainValidationError
from datp_core.domain.evaluation.alert_burden import (
    AlertBurdenResult,
    CalibrationSampleCount,
    CalibrationSampleCountRef,
    CitedTrafficRateEvidence,
    ConfusionCount,
    MeasuredTrafficRateEvidence,
    SampleCount,
    TrafficRate,
    TrafficRateUnit,
)
from datp_core.domain.evaluation.operating_points import (
    BalancedAccuracyScore,
    ClientEligibilityReason,
    ClientEligibilityStatus,
    ClientEvaluationResult,
    ConformalCoverageResult,
    EligibleClientSet,
    F1Score,
    IneligibleClientReason,
    PrecisionScore,
    RecallScore,
    UndefinedCvResult,
    ZeroDenominatorPolicy,
    cv_outcome,
)
from datp_core.domain.evaluation.statistical_results import ClaimOutcome, FalsePositiveRate, TruePositiveRate
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.learning.scores import ClientRoster
from datp_core.domain.thresholding.policies import ThresholdValue


def _identity(character: str) -> StageFingerprint:
    return StageFingerprint(value=character * 64)


def _eligible_set() -> EligibleClientSet:
    first = ClientId(value="client-a")
    second = ClientId(value="client-b")
    return EligibleClientSet(
        roster=ClientRoster(client_ids=(first, second)),
        protocol_eligibility_rule_identity=_identity("a"),
        eligible_clients=(first,),
        ineligible_reasons=(
            IneligibleClientReason(
                client_id=second,
                reason=ClientEligibilityReason.INSUFFICIENT_CALIBRATION_GLOBAL_FALLBACK,
            ),
        ),
        identity=_identity("b"),
    )


def _alert_burden_with_unwrapped_traffic_rate(*, rate: TrafficRate) -> AlertBurdenResult:
    return _construct_alert_burden_with_unwrapped_traffic_rate(AlertBurdenResult, rate=rate)


def _construct_alert_burden_with_unwrapped_traffic_rate(
    constructor: Callable[..., AlertBurdenResult], *, rate: TrafficRate
) -> AlertBurdenResult:
    return constructor(
        traffic_evidence=rate,
        alert_count=ConfusionCount(value=3),
        applicability_period="one hour",
        evaluation_identity=_identity("a"),
    )


def test_client_results_share_the_same_persisted_eligible_set_identity() -> None:
    eligible_set = _eligible_set()
    client = eligible_set.roster.client_ids[0]
    result = ClientEvaluationResult(
        client_id=client,
        true_positive=ConfusionCount(value=8),
        false_positive=ConfusionCount(value=2),
        true_negative=ConfusionCount(value=18),
        false_negative=ConfusionCount(value=2),
        benign_test_count=SampleCount(value=20),
        attack_test_count=SampleCount(value=10),
        assigned_threshold=ThresholdValue(value=1.0),
        false_positive_rate=FalsePositiveRate(value=0.1),
        true_positive_rate=TruePositiveRate(value=0.8),
        precision=PrecisionScore(value=0.8),
        recall=RecallScore(value=0.8),
        f1=F1Score(value=0.8),
        balanced_accuracy=BalancedAccuracyScore(value=0.85),
        eligibility_status=ClientEligibilityStatus.ELIGIBLE,
        eligibility_reason=ClientEligibilityReason.SUFFICIENT_CALIBRATION,
        calibration_sample_count_reference=CalibrationSampleCountRef(
            calibration_artifact_id=CalibrationScoreArtifactId(value="artifact-" + "c" * 64),
            client_id=client,
            recorded_count=CalibrationSampleCount(value=100),
        ),
        eligible_client_set_identity=eligible_set.identity,
        fallback_fingerprint=_identity("d"),
        test_split_identity=_identity("e"),
        zero_denominator_policy=ZeroDenominatorPolicy.ZERO,
    )

    assert result.eligible_client_set_identity is eligible_set.identity
    assert not isinstance(
        ConformalCoverageResult(
            empirical_coverage=0.95,
            target_coverage=0.95,
            conformal_split_identity=_identity("e"),
        ),
        type(eligible_set),
    )


def test_alert_burden_requires_measured_or_cited_evidence() -> None:
    rate = TrafficRate(value=Decimal("12"), unit=TrafficRateUnit.EVENTS_PER_HOUR)
    measured = MeasuredTrafficRateEvidence(
        traffic_rate=rate,
        scope_identity=_identity("f"),
        measurement_provenance="synthetic provenance only",
        applicability_period="one hour",
    )
    cited = CitedTrafficRateEvidence(
        traffic_rate=rate,
        scope_identity=_identity("f"),
        source_reference="citation",
        applicability_period="one hour",
    )

    assert (
        AlertBurdenResult(
            traffic_evidence=measured,
            alert_count=ConfusionCount(value=3),
            applicability_period="one hour",
            evaluation_identity=_identity("a"),
        ).traffic_evidence
        is measured
    )
    assert (
        AlertBurdenResult(
            traffic_evidence=cited,
            alert_count=ConfusionCount(value=3),
            applicability_period="one hour",
            evaluation_identity=_identity("a"),
        ).traffic_evidence
        is cited
    )
    with pytest.raises(DomainValidationError):
        _alert_burden_with_unwrapped_traffic_rate(rate=rate)


def test_zero_mean_cv_is_a_typed_outcome_not_an_exception() -> None:
    result = cv_outcome(
        values=(0.0, 0.0),
        affected_scope_identity=_identity("b"),
        wording_outcome=ClaimOutcome.NULL,
    )

    assert isinstance(result, UndefinedCvResult)
    assert result.mean_value == 0
