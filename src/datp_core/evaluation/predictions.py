"""Threshold stored test scores without invoking training or scoring stages."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from datp_core.models.scoring import AnchorScoreArtifact
from datp_core.thresholding.shared import AnchorThresholds


@dataclass(frozen=True)
class ClientPredictions:
    client_id: str
    benign_predictions: np.ndarray
    attack_predictions: np.ndarray

    def __post_init__(self) -> None:
        self.benign_predictions.setflags(write=False)
        self.attack_predictions.setflags(write=False)


def make_anchor_predictions(scores: AnchorScoreArtifact, thresholds: AnchorThresholds) -> tuple[ClientPredictions, ...]:
    if scores.manifest.score_id != thresholds.score_id:
        raise ValueError("threshold artifact does not reference the supplied score artifact")
    return tuple(
        ClientPredictions(
            client_id=client.client_id,
            benign_predictions=client.test_benign > thresholds.threshold_for(client.client_id),
            attack_predictions=client.test_attack > thresholds.threshold_for(client.client_id),
        )
        for client in scores.clients
    )
