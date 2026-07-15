from typing import Self, TypedDict, Unpack

import numpy as np
from numpy.typing import NDArray

class KMeansOptions(TypedDict):
    n_clusters: int
    init: str
    n_init: int
    max_iter: int
    random_state: int

class KMeans:
    labels_: NDArray[np.signedinteger]
    cluster_centers_: NDArray[np.float64]

    def __init__(self, **options: Unpack[KMeansOptions]) -> None: ...
    def fit(self, features: NDArray[np.float64]) -> Self: ...
