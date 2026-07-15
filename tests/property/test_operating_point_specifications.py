from hypothesis import given
from hypothesis import strategies as st

from datp_core.domain.artifacts.references import CalibrationScoreArtifactId, StageFingerprint
from datp_core.domain.evaluation.alert_burden import (
    CalibrationSampleCount,
    CalibrationSampleCountRef,
    ConfusionCount,
    SampleCount,
)
from datp_core.domain.evaluation.operating_points import (
    BalancedAccuracyScore,
    ClientEligibilityReason,
    ClientEligibilityStatus,
    ClientEvaluationResult,
    F1Score,
    PrecisionScore,
    RecallScore,
    ZeroDenominatorPolicy,
)
from datp_core.domain.evaluation.statistical_results import FalsePositiveRate, TruePositiveRate
from datp_core.domain.experiments.identities import ClientId
from datp_core.domain.thresholding.policies import ThresholdValue


@given(
    true_positive=st.integers(min_value=0, max_value=100),
    false_positive=st.integers(min_value=0, max_value=100),
    true_negative=st.integers(min_value=0, max_value=100),
    false_negative=st.integers(min_value=0, max_value=100),
)
def test_client_evaluation_preserves_recomputable_confusion_count_totals(
    true_positive: int, false_positive: int, true_negative: int, false_negative: int
) -> None:
    client = ClientId(value="client")
    result = ClientEvaluationResult(
        client_id=client,
        true_positive=ConfusionCount(value=true_positive),
        false_positive=ConfusionCount(value=false_positive),
        true_negative=ConfusionCount(value=true_negative),
        false_negative=ConfusionCount(value=false_negative),
        benign_test_count=SampleCount(value=true_negative + false_positive),
        attack_test_count=SampleCount(value=true_positive + false_negative),
        assigned_threshold=ThresholdValue(value=1),
        false_positive_rate=FalsePositiveRate(
            value=false_positive / (true_negative + false_positive) if true_negative + false_positive else 0
        ),
        true_positive_rate=TruePositiveRate(
            value=true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
        ),
        precision=PrecisionScore(
            value=true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
        ),
        recall=RecallScore(
            value=true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
        ),
        f1=F1Score(
            value=2 * true_positive / (2 * true_positive + false_positive + false_negative)
            if 2 * true_positive + false_positive + false_negative
            else 0
        ),
        balanced_accuracy=BalancedAccuracyScore(
            value=(
                (true_positive / (true_positive + false_negative) if true_positive + false_negative else 0)
                + (true_negative / (true_negative + false_positive) if true_negative + false_positive else 1)
            )
            / 2
        ),
        eligibility_status=ClientEligibilityStatus.ELIGIBLE,
        eligibility_reason=ClientEligibilityReason.SUFFICIENT_CALIBRATION,
        calibration_sample_count_reference=CalibrationSampleCountRef(
            calibration_artifact_id=CalibrationScoreArtifactId(value="artifact-" + "a" * 64),
            client_id=client,
            recorded_count=CalibrationSampleCount(value=100),
        ),
        eligible_client_set_identity=StageFingerprint(value="b" * 64),
        fallback_fingerprint=StageFingerprint(value="c" * 64),
        test_split_identity=StageFingerprint(value="d" * 64),
        zero_denominator_policy=ZeroDenominatorPolicy.ZERO,
    )

    assert result.benign_test_count.value == result.true_negative.value + result.false_positive.value
    assert result.attack_test_count.value == result.true_positive.value + result.false_negative.value
    assert result.false_positive_rate.value == (
        false_positive / (true_negative + false_positive) if true_negative + false_positive else 0
    )
    assert result.true_positive_rate.value == (
        true_positive / (true_positive + false_negative) if true_positive + false_negative else 0
    )
    assert result.precision.value == (
        true_positive / (true_positive + false_positive) if true_positive + false_positive else 0
    )
    assert result.recall.value == result.true_positive_rate.value
