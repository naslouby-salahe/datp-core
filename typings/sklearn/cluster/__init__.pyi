from typing import Any

import numpy as np
from numpy.typing import NDArray

class KMeans:
    def __init__(
        self,
        n_clusters: int = 8,
        *,
        init: str = "k-means++",
        n_init: int | str = "auto",
        max_iter: int = 300,
        random_state: int | None = None,
        **kwargs: Any,
    ) -> None: ...
    def set_params(self, **params: Any) -> KMeans: ...
    def fit_predict(
        self,
        X: NDArray[np.float64],
        y: Any | None = None,
        sample_weight: NDArray[np.float64] | None = None,
    ) -> NDArray[np.int_]: ...
