"""Pure association primitives: rank correlation and simple linear regression with leverage diagnostics."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pingouin as pg
import statsmodels.api as sm

from datp_core.analysis.contracts import HypothesisTestResult, LinearRegressionResult
from datp_core.analysis.enums import AlternativeHypothesis, HypothesisTestName
from datp_core.analysis.errors import StatisticalProcedureError


def spearman_correlation(predictor: np.ndarray, outcome: np.ndarray) -> HypothesisTestResult:
    """Compute Spearman rank correlation using Pingouin."""
    if not np.isfinite(predictor).all() or not np.isfinite(outcome).all():
        raise StatisticalProcedureError("Spearman correlation requires finite observations")
    if len(predictor) < 3:
        raise StatisticalProcedureError("Spearman correlation requires at least three observations")
    df = pd.DataFrame({"x": predictor, "y": outcome})
    res = pg.corr(df["x"], df["y"], method="spearman")
    assert isinstance(res, pd.DataFrame)
    statistic = float(res["r"].iloc[0])
    p_value = float(res["p_val"].iloc[0])
    if not np.isfinite((statistic, p_value)).all():
        raise StatisticalProcedureError("Spearman correlation is undefined for the supplied observations")
    return HypothesisTestResult(
        test_name=HypothesisTestName.SPEARMAN_CORRELATION,
        statistic=statistic,
        p_value=p_value,
        alternative=AlternativeHypothesis.TWO_SIDED,
    )


def simple_linear_regression(predictor: np.ndarray, outcome: np.ndarray) -> LinearRegressionResult:
    """Compute simple linear regression using Pingouin with statsmodels leverage diagnostics."""
    if not np.isfinite(predictor).all() or not np.isfinite(outcome).all():
        raise StatisticalProcedureError("Linear regression requires finite observations")
    if len(predictor) < 3 or predictor.shape != outcome.shape:
        raise StatisticalProcedureError(
            "Linear regression requires at least three paired finite observations of equal length"
        )
    # Check non-constant predictor
    if math.isclose(float(np.std(predictor)), 0.0, abs_tol=0.0):
        raise StatisticalProcedureError("Linear regression requires non-constant predictor observations")

    df = pd.DataFrame({"x": predictor, "y": outcome})
    pg_res = pg.linear_regression(df["x"], df["y"])
    assert isinstance(pg_res, pd.DataFrame)
    slope = float(pg_res["coef"].iloc[1])
    intercept = float(pg_res["coef"].iloc[0])
    standard_error = float(pg_res["se"].iloc[1])
    r_squared = float(pg_res["r2"].iloc[0])

    # Leverage diagnostics via statsmodels
    x_with_const = sm.add_constant(predictor)
    ols_model = sm.OLS(outcome, x_with_const)
    ols_result = ols_model.fit()
    influence = ols_result.get_influence()
    leverage = tuple(float(h) for h in influence.hat_matrix_diag)

    # Leave-one-out slopes
    leave_one_out_slopes: list[float] = []
    for index in range(len(predictor)):
        x_loo = np.delete(predictor, index)
        y_loo = np.delete(outcome, index)
        loo_df = pd.DataFrame({"x": x_loo, "y": y_loo})
        loo_res = pg.linear_regression(loo_df["x"], loo_df["y"])
        assert isinstance(loo_res, pd.DataFrame)
        leave_one_out_slopes.append(float(loo_res["coef"].iloc[1]))

    if not np.isfinite((slope, intercept, standard_error, r_squared)).all():
        raise StatisticalProcedureError("Linear regression produced non-finite results")

    return LinearRegressionResult(
        slope=slope,
        intercept=intercept,
        standard_error=standard_error,
        r_squared=r_squared,
        leverage=leverage,
        leave_one_out_slopes=tuple(leave_one_out_slopes),
    )
