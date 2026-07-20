"""Pingouin effect size calculation and repeated-measures diagnostics adapter."""

from __future__ import annotations

import numpy as np
import pingouin as pg


def compute_paired_effect_size(x: np.ndarray, y: np.ndarray) -> float:
    """Compute Cohen's d for paired samples using Pingouin."""
    res = pg.compute_effsize(x, y, paired=True, eftype="cohen")
    return float(np.asarray(res).item())
