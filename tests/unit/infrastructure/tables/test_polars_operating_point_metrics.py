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
