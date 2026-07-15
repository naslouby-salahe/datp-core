import numpy as np
from numpy.typing import NDArray

class StandardScaler:
    def fit_transform(self, features: NDArray[np.float64]) -> NDArray[np.float64]: ...
