"""Canonical DataFrame column-name enums for artifact schemas.

Every persisted column name lives here. Analysis capabilities reference these
enums instead of repeating raw string literals. Use ``.value`` only at the
Polars / serialisation boundary.
"""

from __future__ import annotations

from enum import StrEnum


class ThresholdColumn(StrEnum):
    """Columns in validated threshold frames."""

    CLIENT_ID = "client_id"
    THRESHOLD = "threshold"
    FINITE_SAMPLE_RANK = "finite_sample_rank"
    ATTAINABILITY_STATUS = "attainability_status"
    CLUSTER_LABEL = "cluster_label"


class MetricColumn(StrEnum):
    """Columns in validated client-metric frames."""

    CLIENT_ID = "client_id"
    TRUE_NEGATIVES = "true_negatives"
    FALSE_POSITIVES = "false_positives"
    FALSE_POSITIVE_RATE = "false_positive_rate"
    FALSE_POSITIVE_RATE_STATUS = "false_positive_rate_status"


class ScoreColumn(StrEnum):
    """Columns in validated score frames (calibration and test)."""

    CLIENT_ID = "client_id"
    SCORE = "score"
    TARGET_QUANTILE = "target_quantile"
