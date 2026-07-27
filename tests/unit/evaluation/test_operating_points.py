"""Operating-point evaluation with canonical schema."""

import polars as pl
import pytest

from datp_core.evaluation.enums import MetricStatus, MissingThresholdPolicy
from datp_core.evaluation.operating_points import evaluate_operating_points


def _make_scores() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "client_id": ["client_a", "client_a", "client_b", "client_b"],
            "score": [0.1, 0.9, 0.4, 0.7],
            "label": [0, 1, 0, 1],
        },
        schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
    )


def _make_thresholds() -> pl.DataFrame:
    return pl.DataFrame(
        {"client_id": ["client_a", "client_b"], "threshold": [0.5, 0.5]},
        schema={"client_id": pl.String, "threshold": pl.Float64},
    )


class TestEvaluateOperatingPoints:
    def test_all_clients_eligible(self) -> None:
        result = evaluate_operating_points(
            _make_scores(), _make_thresholds(), missing_threshold_policy=MissingThresholdPolicy.FAIL
        )
        assert result.height == 2
        assert result["client_id"].to_list() == ["client_a", "client_b"]

    def test_score_greater_than_threshold_is_attack(self) -> None:
        result = evaluate_operating_points(
            _make_scores(), _make_thresholds(), missing_threshold_policy=MissingThresholdPolicy.FAIL
        )
        row = result.filter(pl.col("client_id") == "client_a").row(0, named=True)
        assert row["true_positives"] == 1
        assert row["false_positives"] == 0

    def test_score_equal_to_threshold_is_benign(self) -> None:
        scores = pl.DataFrame(
            {"client_id": ["c"], "score": [0.5], "label": [1]},
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        thresholds = pl.DataFrame(
            {"client_id": ["c"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        result = evaluate_operating_points(scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.FAIL)
        row = result.row(0, named=True)
        assert row["true_positives"] == 0

    def test_missing_class_benign(self) -> None:
        scores = pl.DataFrame(
            {"client_id": ["attack_only"], "score": [0.9], "label": [1]},
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        thresholds = pl.DataFrame(
            {"client_id": ["attack_only"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        result = evaluate_operating_points(scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.FAIL)
        row = result.row(0, named=True)
        assert row["false_positive_rate"] is None
        assert row["false_positive_rate_status"] == MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS.value

    def test_missing_threshold_fail_policy(self) -> None:
        scores = _make_scores()
        thresholds = pl.DataFrame(
            {"client_id": ["client_a"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        with pytest.raises(ValueError, match="Missing thresholds for clients"):
            evaluate_operating_points(scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.FAIL)

    def test_missing_threshold_mark_ineligible(self) -> None:
        scores = _make_scores()
        thresholds = pl.DataFrame(
            {"client_id": ["client_a"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        result = evaluate_operating_points(
            scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.MARK_INELIGIBLE
        )
        assert result.height == 2
        ineligible = result.filter(pl.col("client_id") == "client_b").row(0, named=True)
        assert ineligible["false_positive_rate_status"] == MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value

    def test_empty_scores_raises(self) -> None:
        empty = pl.DataFrame(schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64})
        thresholds = _make_thresholds()
        with pytest.raises(ValueError, match="empty score frame"):
            evaluate_operating_points(empty, thresholds, missing_threshold_policy=MissingThresholdPolicy.FAIL)

    def test_nan_scores_raises(self) -> None:
        scores = pl.DataFrame(
            {"client_id": ["c"], "score": [float("nan")], "label": [0]},
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        thresholds = pl.DataFrame(
            {"client_id": ["c"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        with pytest.raises(ValueError, match="must be finite"):
            evaluate_operating_points(scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.FAIL)

    def test_inf_scores_raises(self) -> None:
        scores = pl.DataFrame(
            {"client_id": ["c"], "score": [float("inf")], "label": [0]},
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        thresholds = pl.DataFrame(
            {"client_id": ["c"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        with pytest.raises(ValueError, match="must be finite"):
            evaluate_operating_points(scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.FAIL)

    def test_auroc_preserved_for_all_clients(self) -> None:
        result = evaluate_operating_points(
            _make_scores(), _make_thresholds(), missing_threshold_policy=MissingThresholdPolicy.FAIL
        )
        assert "auroc" in result.columns
        assert "auroc_status" in result.columns
        assert result["auroc_status"].to_list() == [
            MetricStatus.AVAILABLE.value,
            MetricStatus.AVAILABLE.value,
        ]

    def test_auroc_unavailable_for_single_class_client(self) -> None:
        scores = pl.DataFrame(
            {"client_id": ["single", "single"], "score": [0.1, 0.2], "label": [0, 0]},
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        thresholds = pl.DataFrame(
            {"client_id": ["single"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        result = evaluate_operating_points(scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.FAIL)
        assert result["auroc_status"][0] == MetricStatus.UNAVAILABLE_SINGLE_CLASS.value

    def test_deterministic_ordering(self) -> None:
        scores = pl.DataFrame(
            {
                "client_id": ["z", "a", "m"],
                "score": [0.1, 0.5, 0.9],
                "label": [0, 0, 0],
            },
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        thresholds = pl.DataFrame(
            {"client_id": ["z", "a", "m"], "threshold": [0.5, 0.5, 0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        result = evaluate_operating_points(scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.FAIL)
        assert result["client_id"].to_list() == ["a", "m", "z"]

    def test_eligible_and_ineligible_share_schema(self) -> None:
        scores = _make_scores()
        thresholds = pl.DataFrame(
            {"client_id": ["client_a"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        result = evaluate_operating_points(
            scores, thresholds, missing_threshold_policy=MissingThresholdPolicy.MARK_INELIGIBLE
        )
        eligible_cols = set(
            result.filter(
                pl.col("false_positive_rate_status") != MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value
            ).columns
        )
        ineligible_cols = set(
            result.filter(
                pl.col("false_positive_rate_status") == MetricStatus.UNAVAILABLE_INELIGIBLE_CLIENT.value
            ).columns
        )
        assert eligible_cols == ineligible_cols
