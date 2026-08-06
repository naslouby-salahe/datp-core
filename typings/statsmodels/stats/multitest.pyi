from collections.abc import Sequence
from typing import Any

import numpy as np
from numpy.typing import NDArray

def multipletests(
    pvals: Sequence[float] | NDArray[np.float64],
    alpha: float = 0.05,
    method: str = "hs",
    maxiter: int = 1,
    is_sorted: bool = False,
    returnsorted: bool = False,
) -> tuple[NDArray[np.bool_], NDArray[np.float64], Any, float]: ...
