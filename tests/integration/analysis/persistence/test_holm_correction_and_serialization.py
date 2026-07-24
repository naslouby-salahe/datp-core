"""Holm correction ordering and JSON-serialization determinism for the persisted
statistical-analysis artifact."""

from __future__ import annotations

import json

from datp_core.analysis.comparisons.models import PairedThresholdAnalysisResult
from datp_core.analysis.execution.persistence import apply_holm_correction
from datp_core.analysis.result import analysis_result_to_payload
from datp_core.analysis.statistics.models import ConfidenceInterval
from datp_core.core.values import Probability


def _paired_result(*, analysis_label: str, p_value: float | None) -> PairedThresholdAnalysisResult:
    return PairedThresholdAnalysisResult(
        analysis_label=analysis_label,
        metric="cv_fpr",
        first_threshold_policy="a",
        second_threshold_policy="b",
        training_seeds=(1, 2, 3),
        first_seed_values=(0.1, 0.2, 0.3),
        second_seed_values=(0.0, 0.1, 0.2),
        first_mean=0.2,
        second_mean=0.1,
        mean_difference=0.1,
        confidence_interval=ConfidenceInterval(
            lower_bound=0.01, upper_bound=0.2, confidence_level=Probability(0.95), method="bca_bootstrap"
        ),
        p_value=p_value,
        rank_biserial=0.5,
        resample_count=2000,
        analysis_seed=42,
        seed_differences=(0.1, 0.1, 0.1),
        sign_consistency=1.0,
        zero_difference_count=0,
        negative_difference_count=0,
    )


def _as_paired(result: object) -> PairedThresholdAnalysisResult:
    assert isinstance(result, PairedThresholdAnalysisResult)
    return result


def test_holm_correction_preserves_input_order_and_only_touches_paired_results_with_p_values() -> None:
    results = [
        _paired_result(analysis_label="first", p_value=0.03),
        _paired_result(analysis_label="second", p_value=None),
        _paired_result(analysis_label="third", p_value=0.01),
        _paired_result(analysis_label="fourth", p_value=0.04),
    ]

    corrected = [_as_paired(result) for result in apply_holm_correction(list(results))]

    assert [result.analysis_label for result in corrected] == ["first", "second", "third", "fourth"]
    assert corrected[1].holm_adjusted_p_value is None
    assert corrected[0].holm_adjusted_p_value is not None
    assert corrected[2].holm_adjusted_p_value is not None
    assert corrected[3].holm_adjusted_p_value is not None


def test_holm_correction_is_a_no_op_with_fewer_than_two_candidate_p_values() -> None:
    results = [_paired_result(analysis_label="only", p_value=0.03)]

    corrected = [_as_paired(result) for result in apply_holm_correction(list(results))]

    assert corrected[0].holm_adjusted_p_value is None


def test_serialized_payload_is_deterministic_and_restores_the_dotted_anchor_check_key() -> None:
    result = _paired_result(analysis_label="deterministic", p_value=0.02)

    first = json.dumps(analysis_result_to_payload(result), separators=(",", ":"), sort_keys=True)
    second = json.dumps(analysis_result_to_payload(result), separators=(",", ":"), sort_keys=True)

    assert first == second
    assert json.loads(first)["analysis_label"] == "deterministic"
