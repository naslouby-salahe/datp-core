"""scikit-learn classical utilities and metric calculations."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import adjusted_rand_score, roc_auc_score
from sklearn.preprocessing import StandardScaler


def scale_features(
    train_data: np.ndarray,
    test_data: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray | None, StandardScaler]:
    scaler = StandardScaler()
    scaled_train = scaler.fit_transform(train_data)
    scaled_test = scaler.transform(test_data) if test_data is not None else None
    return scaled_train, scaled_test, scaler  # type: ignore


def compute_roc_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    if len(np.unique(labels)) < 2:
        return 0.5
    return float(roc_auc_score(labels, scores))


def compute_adjusted_rand_index(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    return float(adjusted_rand_score(labels_true, labels_pred))
