"""Operating-point tabular metrics preserve unavailable reasons."""

import polars as pl

from datp_core.infrastructure.tables.polars_engine import compute_operating_point_metrics


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
