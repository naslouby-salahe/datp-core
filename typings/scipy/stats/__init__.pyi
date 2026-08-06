from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

def wilcoxon(
    x: NDArray[np.float64] | Sequence[float],
    y: NDArray[np.float64] | Sequence[float] | None = None,
    zero_method: str = "wilcox",
    correction: bool = False,
    alternative: str = "two-sided",
    method: str = "auto",
    *,
    axis: int = 0,
) -> Any: ...
def rankdata(
    a: NDArray[np.float64] | Sequence[float],
    method: str = "average",
    *,
    axis: int | None = None,
    nan_policy: str = "propagate",
) -> NDArray[np.float64]: ...
def spearmanr(
    a: NDArray[np.float64] | Sequence[float],
    b: NDArray[np.float64] | Sequence[float] | None = None,
    axis: int = 0,
    nan_policy: str = "propagate",
    alternative: str = "two-sided",
) -> Any: ...
def linregress(
    x: NDArray[np.float64] | Sequence[float],
    y: NDArray[np.float64] | Sequence[float],
    alternative: str = "two-sided",
    *,
    axis: int = 0,
) -> Any: ...
def skew(
    a: NDArray[np.float64] | Sequence[float],
    axis: int = 0,
    bias: bool = True,
    nan_policy: str = "propagate",
) -> Any: ...

class _Norm:
    def ppf(self, q: float, *args: Any, **kwargs: Any) -> float: ...
    def cdf(self, x: float | NDArray[np.float64], *args: Any, **kwargs: Any) -> NDArray[np.float64]: ...

class _T:
    def ppf(self, q: float, df: float, *args: Any, **kwargs: Any) -> float: ...

norm: _Norm
t: _T
