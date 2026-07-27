"""Score distributions and threshold trade-offs."""

import polars as pl
import pytest

from datp_core.evaluation.distributions import client_score_distributions


class TestClientScoreDistributions:
    def test_deterministic_client_ordering(self) -> None:
        thresholds = pl.DataFrame(
            {"client_id": ["z", "a"], "threshold": [0.5, 0.3]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        metrics = pl.DataFrame(
            {
                "client_id": ["a", "z"],
                "false_positive_rate": [0.1, 0.2],
                "false_positive_rate_status": ["available", "available"],
                "true_positive_rate": [0.9, 0.8],
                "true_positive_rate_status": ["available", "available"],
                "balanced_accuracy": [0.9, 0.8],
                "balanced_accuracy_status": ["available", "available"],
                "macro_f1": [0.5, 0.5],
                "macro_f1_status": ["available", "available"],
            },
            schema={
                "client_id": pl.String,
                "false_positive_rate": pl.Float64,
                "false_positive_rate_status": pl.String,
                "true_positive_rate": pl.Float64,
                "true_positive_rate_status": pl.String,
                "balanced_accuracy": pl.Float64,
                "balanced_accuracy_status": pl.String,
                "macro_f1": pl.Float64,
                "macro_f1_status": pl.String,
            },
        )
        scores = pl.DataFrame(
            {
                "client_id": ["a", "a", "z", "z"],
                "score": [0.1, 0.9, 0.2, 0.8],
                "label": [0, 1, 0, 1],
            },
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        result = client_score_distributions(thresholds, metrics, scores, client_filter=None)
        client_ids = [str(d.client_id) for d in result]
        assert client_ids == ["a", "z"]

    def test_client_filter_success(self) -> None:
        thresholds = pl.DataFrame(
            {"client_id": ["a", "b"], "threshold": [0.5, 0.3]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        metrics = pl.DataFrame(
            {
                "client_id": ["a", "b"],
                "false_positive_rate": [0.1, 0.2],
                "false_positive_rate_status": ["available", "available"],
                "true_positive_rate": [0.9, 0.8],
                "true_positive_rate_status": ["available", "available"],
                "balanced_accuracy": [0.9, 0.8],
                "balanced_accuracy_status": ["available", "available"],
                "macro_f1": [0.5, 0.5],
                "macro_f1_status": ["available", "available"],
            },
            schema={
                "client_id": pl.String,
                "false_positive_rate": pl.Float64,
                "false_positive_rate_status": pl.String,
                "true_positive_rate": pl.Float64,
                "true_positive_rate_status": pl.String,
                "balanced_accuracy": pl.Float64,
                "balanced_accuracy_status": pl.String,
                "macro_f1": pl.Float64,
                "macro_f1_status": pl.String,
            },
        )
        scores = pl.DataFrame(
            {
                "client_id": ["a", "a", "b", "b"],
                "score": [0.1, 0.9, 0.2, 0.8],
                "label": [0, 1, 0, 1],
            },
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        result = client_score_distributions(thresholds, metrics, scores, client_filter="a")
        assert len(result) == 1
        assert str(result[0].client_id) == "a"

    def test_unavailable_client_filter_raises(self) -> None:
        thresholds = pl.DataFrame(
            {"client_id": ["a"], "threshold": [0.5]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
        metrics = pl.DataFrame(
            {
                "client_id": ["a"],
                "false_positive_rate": [0.1],
                "false_positive_rate_status": ["available"],
                "true_positive_rate": [0.9],
                "true_positive_rate_status": ["available"],
                "balanced_accuracy": [0.9],
                "balanced_accuracy_status": ["available"],
                "macro_f1": [0.5],
                "macro_f1_status": ["available"],
            },
            schema={
                "client_id": pl.String,
                "false_positive_rate": pl.Float64,
                "false_positive_rate_status": pl.String,
                "true_positive_rate": pl.Float64,
                "true_positive_rate_status": pl.String,
                "balanced_accuracy": pl.Float64,
                "balanced_accuracy_status": pl.String,
                "macro_f1": pl.Float64,
                "macro_f1_status": pl.String,
            },
        )
        scores = pl.DataFrame(
            {"client_id": ["a", "a"], "score": [0.1, 0.9], "label": [0, 1]},
            schema={"client_id": pl.String, "score": pl.Float64, "label": pl.Int64},
        )
        with pytest.raises(ValueError, match="Locked client"):
            client_score_distributions(thresholds, metrics, scores, client_filter="nonexistent")
