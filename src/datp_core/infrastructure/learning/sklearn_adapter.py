"""scikit-learn classical utilities and metric calculations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import numpy as np
from sklearn.metrics import adjusted_rand_score, roc_auc_score
from sklearn.preprocessing import StandardScaler


class AurocStatus(Enum):
    AVAILABLE = "available"
    UNAVAILABLE_SINGLE_CLASS = "unavailable_single_class"


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientAuroc:
    value: float | None
    status: AurocStatus

    @classmethod
    def available(cls, value: float) -> ClientAuroc:
        return cls(value=value, status=AurocStatus.AVAILABLE)

    @classmethod
    def unavailable_single_class(cls) -> ClientAuroc:
        return cls(value=None, status=AurocStatus.UNAVAILABLE_SINGLE_CLASS)


def scale_features(
    train_data: np.ndarray,
    test_data: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray | None, StandardScaler]:
    scaler = StandardScaler()
    scaled_train = scaler.fit_transform(train_data)
    scaled_test = scaler.transform(test_data) if test_data is not None else None
    return scaled_train, scaled_test, scaler  # type: ignore


def compute_roc_auc(labels: np.ndarray, scores: np.ndarray) -> ClientAuroc:
    if len(np.unique(labels)) < 2:
        return ClientAuroc.unavailable_single_class()
    return ClientAuroc.available(float(roc_auc_score(labels, scores)))


def compute_adjusted_rand_index(labels_true: np.ndarray, labels_pred: np.ndarray) -> float:
    return float(adjusted_rand_score(labels_true, labels_pred))
