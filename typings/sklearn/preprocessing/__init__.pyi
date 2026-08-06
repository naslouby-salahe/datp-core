from typing import Any

import numpy as np
from numpy.typing import NDArray

class StandardScaler:
    def __init__(self, *, copy: bool = True, with_mean: bool = True, with_std: bool = True) -> None: ...
    def fit_transform(self, X: NDArray[np.float64], y: Any | None = None, **fit_params: Any) -> NDArray[np.float64]: ...
