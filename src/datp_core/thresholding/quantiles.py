"""Validated linear-interpolation quantiles for Phase 2 anchor policies."""

from __future__ import annotations

import numpy as np


class QuantileError(ValueError):
    """Raised when a calibration-score quantile request is invalid."""


def benign_quantile(scores: np.ndarray, q: float) -> float:
    if not 0.0 < q < 1.0:
        raise QuantileError("q must be strictly between zero and one")
    if scores.ndim != 1 or not len(scores):
        raise QuantileError("benign calibration scores must be a non-empty one-dimensional array")
    return float(np.quantile(scores, q, method="linear"))
