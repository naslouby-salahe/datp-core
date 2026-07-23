"""Operating-point tabular metrics preserve unavailable reasons."""

import polars as pl

from datp_core.evaluation.operating_points import ineligible_client_metrics
from datp_core.evaluation.operating_points import compute_operating_point_metrics


def test_missing_class_metrics_are_null_with_a_typed_status() -> None:
    result = compute_operating_point_metrics(
        pl.DataFrame(
            {
                "client_id": ["benign", "attack"],
                "score": [0.1, 0.9],
                "threshold": [0.5, 0.5],
                "label": [0, 1],
            }
        )
    ).sort("client_id")

    attack, benign = result.rows(named=True)
    assert attack["false_positive_rate"] is None
    assert attack["false_positive_rate_status"] == "unavailable_missing_benign_class"
    assert benign["true_positive_rate"] is None
    assert benign["true_positive_rate_status"] == "unavailable_missing_attack_class"


def test_complete_class_metrics_follow_the_configured_strict_threshold_rule() -> None:
    result = compute_operating_point_metrics(
        pl.DataFrame(
            {
                "client_id": ["client"] * 4,
                "score": [0.5, 0.6, 0.4, 0.7],
                "threshold": [0.5] * 4,
                "label": [0, 0, 1, 1],
            }
        )
    ).row(0, named=True)

    assert result["false_positives"] == 1
    assert result["true_negatives"] == 1
    assert result["true_positives"] == 1
    assert result["false_negatives"] == 1
    assert result["false_positive_rate"] == 0.5
    assert result["true_positive_rate"] == 0.5
    assert result["balanced_accuracy"] == 0.5
    assert result["macro_f1"] == 0.5


def test_calibration_size_ineligible_client_retains_a_typed_metric_row() -> None:
    result = ineligible_client_metrics(
        pl.DataFrame(
            {"client_id": ["sample_starved"], "threshold": [None]},
            schema={"client_id": pl.String, "threshold": pl.Float64},
        )
    ).row(0, named=True)

    assert result["false_positive_rate"] is None
    assert result["false_positive_rate_status"] == "unavailable_ineligible_client"
    assert result["macro_f1_status"] == "unavailable_ineligible_client"
