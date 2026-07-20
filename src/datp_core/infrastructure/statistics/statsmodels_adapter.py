"""statsmodels linear mixed-effects model adapter."""

from __future__ import annotations

import pandas as pd
import statsmodels.formula.api as smf

from datp_core.domain.statistics import HypothesisTestResult


def fit_mixed_effects_model(
    df: pd.DataFrame,
    formula: str = "fpr ~ C(policy)",
    group_col: str = "seed",
) -> HypothesisTestResult:
    """Fit a linear mixed-effects model with random intercepts for seeds."""
    model = smf.mixedlm(formula, df, groups=df[group_col])
    res = model.fit()
    p_val = float(res.pvalues.iloc[1]) if len(res.pvalues) > 1 else 1.0
    stat = float(res.tvalues.iloc[1]) if len(res.tvalues) > 1 else 0.0
    return HypothesisTestResult(
        test_name="linear_mixed_effects",
        statistic=abs(stat),
        p_value=max(0.0, min(1.0, p_val)),
    )
