from collections.abc import Callable, Sequence
from typing import Literal, TypedDict, Unpack

import numpy as np
from numpy.typing import NDArray

class ConfidenceInterval:
    low: float
    high: float

class BootstrapResult:
    confidence_interval: ConfidenceInterval

class WilcoxonResult:
    statistic: float
    pvalue: float

class SignificanceResult:
    statistic: float
    pvalue: float

class BootstrapOptions(TypedDict):
    n_resamples: int
    confidence_level: float
    method: Literal["BCa"]
    rng: np.random.Generator

def bootstrap(
    data: tuple[NDArray[np.float64], ...],
    statistic: Callable[[NDArray[np.float64]], np.floating[object]],
    **options: Unpack[BootstrapOptions],
) -> BootstrapResult: ...
def wilcoxon(first: Sequence[float], second: Sequence[float]) -> WilcoxonResult: ...
def spearmanr(first: Sequence[float], second: Sequence[float]) -> SignificanceResult: ...
