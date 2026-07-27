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
    POLICY_KIND = "policy_kind"
    SCOPE = "scope"
    EFFECTIVE_LAMBDA = "effective_lambda"
    CLUSTER_LABEL = "cluster_label"
    FINITE_SAMPLE_RANK = "finite_sample_rank"
    POLICY_ID = "policy_id"
    TARGET_QUANTILE = "target_quantile"


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
    SOURCE_PATH = "source_path"
    SOURCE_ROW_INDEX = "source_row_index"
    TARGET_QUANTILE = "target_quantile"
