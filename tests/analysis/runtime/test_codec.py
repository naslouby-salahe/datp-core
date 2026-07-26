"""Unit tests for cattrs analysis codec."""

from __future__ import annotations

import pytest

from datp_core.analysis.contracts import (
    ConfidenceInterval,
    FederatedProximalLossObservation,
    FederatedProximalSelectionResult,
    HypothesisTestResult,
    PairedThresholdAnalysisResult,
)
from datp_core.analysis.enums import AlternativeHypothesis, AnalysisResultKind, ConfidenceIntervalMethod, HypothesisTestName
from datp_core.analysis.errors import ResultDecodingError
from datp_core.analysis.runtime.codec import (
    EncodedAnalysisResult,
    decode_analysis_result,
    decode_result_json,
    encode_analysis_result,
    encode_result_json,
)
from datp_core.analysis.runtime.runner import register_analysis_capabilities
from datp_core.core.identifiers import AnalysisLabel, MetricId, ThresholdPolicyId
from datp_core.core.numbers import Probability
from datp_core.core.seeding import Seed


@pytest.fixture(autouse=True)
def _ensure_capabilities() -> None:
    register_analysis_capabilities()


def test_codec_envelope_structure() -> None:
    result = FederatedProximalSelectionResult(
        analysis_label=AnalysisLabel("test_selection"),
        selected_proximal_mu=0.01,
        locked_primary_round=10,
        calibration_losses=(
            FederatedProximalLossObservation(proximal_mu=0.01, mean_benign_calibration_loss=0.05),
        ),
    )
    envelope = encode_analysis_result(result)

    assert envelope.result_kind == AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION
    assert envelope.payload_version == 1
    assert isinstance(envelope.data, dict)
    assert envelope.data["selected_proximal_mu"] == 0.01

    decoded = decode_analysis_result(envelope)
    assert isinstance(decoded, FederatedProximalSelectionResult)
    assert decoded.selected_proximal_mu == 0.01
    assert decoded.analysis_label == AnalysisLabel("test_selection")


def test_codec_paired_result_roundtrip() -> None:
    ci = ConfidenceInterval(
        lower_bound=0.01,
        upper_bound=0.05,
        confidence_level=Probability(0.95),
        method=ConfidenceIntervalMethod.BCA_BOOTSTRAP,
    )
    ht = HypothesisTestResult(
        test_name=HypothesisTestName.WILCOXON_SIGNED_RANK,
        statistic=12.0,
        p_value=0.03,
        alternative=AlternativeHypothesis.TWO_SIDED,
    )
    paired = PairedThresholdAnalysisResult(
        analysis_label=AnalysisLabel("paired_test"),
        metric=MetricId("cv_fpr"),
        first_threshold_policy=ThresholdPolicyId("policy_a"),
        second_threshold_policy=ThresholdPolicyId("policy_b"),
        training_seeds=(Seed(42), Seed(43)),
        first_seed_values=(0.1, 0.12),
        second_seed_values=(0.08, 0.09),
        first_mean=0.11,
        second_mean=0.085,
        mean_difference=0.025,
        confidence_interval=ci,
        p_value=0.03,
        rank_biserial=0.8,
        resample_count=1000,
        analysis_seed=Seed(100),
        seed_differences=(0.02, 0.03),
        sign_consistency=1.0,
        zero_difference_count=0,
        negative_difference_count=0,
    )

    json_str = encode_result_json(paired)
    decoded = decode_result_json(json_str)

    assert isinstance(decoded, PairedThresholdAnalysisResult)
    assert decoded.analysis_label == AnalysisLabel("paired_test")
    assert decoded.metric == MetricId("cv_fpr")
    assert decoded.confidence_interval.method == ConfidenceIntervalMethod.BCA_BOOTSTRAP
    assert decoded.training_seeds == (Seed(42), Seed(43))


def test_codec_rejects_unsupported_version() -> None:
    envelope = EncodedAnalysisResult(
        result_kind=AnalysisResultKind.FEDERATED_PROXIMAL_SELECTION,
        payload_version=999,
        data={},
    )
    with pytest.raises(ResultDecodingError):
        decode_analysis_result(envelope)
