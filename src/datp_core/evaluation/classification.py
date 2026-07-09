"""Per-client classification metrics; AUROC is explicitly a control metric."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp_core.evaluation.predictions import ClientPredictions
from datp_core.models.scoring import AnchorScoreArtifact


class MetricError(ValueError):
    """Raised when a requested metric has no denominator or valid inputs."""


@dataclass(frozen=True)
class ClientMetrics:
    client_id: str
    fpr: float
    tpr: float
    balanced_accuracy: float
    macro_f1: float
    auroc_control: float


def _binary_auc(labels: np.ndarray, scores: np.ndarray) -> float:
    positive = int(labels.sum())
    negative = len(labels) - positive
    if positive == 0 or negative == 0:
        raise MetricError("AUROC requires both benign and attack test samples")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores), dtype=float)
    ranks[order] = np.arange(1, len(scores) + 1)
    for score in np.unique(scores):
        tied = np.flatnonzero(scores == score)
        ranks[tied] = ranks[tied].mean()
    return float((ranks[labels].sum() - positive * (positive + 1) / 2) / (positive * negative))


def _macro_f1(benign_predictions: np.ndarray, attack_predictions: np.ndarray) -> float:
    labels = np.concatenate(
        (np.zeros(len(benign_predictions), dtype=bool), np.ones(len(attack_predictions), dtype=bool))
    )
    predictions = np.concatenate((benign_predictions, attack_predictions))
    f1_values: list[float] = []
    for target in (False, True):
        true_positive = int(((predictions == target) & (labels == target)).sum())
        false_positive = int(((predictions == target) & (labels != target)).sum())
        false_negative = int(((predictions != target) & (labels == target)).sum())
        denominator = 2 * true_positive + false_positive + false_negative
        f1_values.append(0.0 if denominator == 0 else 2 * true_positive / denominator)
    return float(np.mean(f1_values))


def evaluate_client_metrics(
    scores: AnchorScoreArtifact, predictions: tuple[ClientPredictions, ...]
) -> tuple[ClientMetrics, ...]:
    metrics: list[ClientMetrics] = []
    for client in scores.clients:
        prediction = next((item for item in predictions if item.client_id == client.client_id), None)
        if prediction is None:
            raise MetricError(f"missing predictions for client {client.client_id}")
        if not len(client.test_benign) or not len(client.test_attack):
            raise MetricError(f"client {client.client_id} has an empty test denominator")
        fpr = float(prediction.benign_predictions.mean())
        tpr = float(prediction.attack_predictions.mean())
        labels = np.concatenate(
            (np.zeros(len(client.test_benign), dtype=bool), np.ones(len(client.test_attack), dtype=bool))
        )
        raw_scores = np.concatenate((client.test_benign, client.test_attack))
        metrics.append(
            ClientMetrics(
                client_id=client.client_id,
                fpr=fpr,
                tpr=tpr,
                balanced_accuracy=(1.0 + tpr - fpr) / 2.0,
                macro_f1=_macro_f1(prediction.benign_predictions, prediction.attack_predictions),
                auroc_control=_binary_auc(labels, raw_scores),
            )
        )
    return tuple(metrics)
