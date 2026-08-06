from collections.abc import Sequence

import numpy as np
from numpy.typing import NDArray

def jensenshannon(
    p: NDArray[np.float64] | Sequence[float],
    q: NDArray[np.float64] | Sequence[float],
    base: float | None = None,
    *,
    axis: int = 0,
    keepdims: bool = False,
) -> float: ...
