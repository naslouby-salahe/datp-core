"""scikit-posthocs post-hoc non-parametric pairwise comparisons adapter."""

from __future__ import annotations

import pandas as pd
import scikit_posthocs as sp


def compute_nemenyi_posthoc(df: pd.DataFrame, val_col: str, group_col: str) -> pd.DataFrame:
    """Nemenyi post-hoc pairwise rank comparison test."""
    return sp.posthoc_nemenyi_friedman(df, y_col=val_col, group_col=group_col, block_col="seed")
