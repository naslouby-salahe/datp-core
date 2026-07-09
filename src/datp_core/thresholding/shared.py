"""B1 shared threshold: arithmetic mean of eligible local benign p95 values."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from datp_core.domain.policies import ThresholdPolicy
from datp_core.models.scoring import AnchorScoreArtifact, ScoreArtifactError
from datp_core.thresholding.quantiles import benign_quantile


@dataclass(frozen=True)
class AnchorThresholds:
    policy: ThresholdPolicy
    score_id: str
    q: float
    per_client: tuple[tuple[str, float], ...]
    shared_threshold: float

    def __post_init__(self) -> None:
        if not self.score_id:
            raise ScoreArtifactError("threshold artifact requires a score ID")
        if not 0.0 < self.q < 1.0:
            raise ScoreArtifactError("threshold quantile must be strictly between zero and one")
        if not self.per_client:
            raise ScoreArtifactError("threshold artifact requires at least one client threshold")
        client_ids = tuple(client_id for client_id, _ in self.per_client)
        if len(client_ids) != len(set(client_ids)):
            raise ScoreArtifactError("threshold artifact client IDs must be unique")
        if not isfinite(self.shared_threshold) or any(not isfinite(threshold) for _, threshold in self.per_client):
            raise ScoreArtifactError("threshold values must be finite")

    def threshold_for(self, client_id: str) -> float:
        for known_client_id, threshold in self.per_client:
            if known_client_id == client_id:
                return threshold
        raise ScoreArtifactError(f"no threshold exists for client {client_id!r}")


@dataclass(frozen=True)
class AnchorThresholdArtifact:
    score_id: str
    thresholds: tuple[AnchorThresholds, ...]

    def __post_init__(self) -> None:
        if not self.score_id or not self.thresholds:
            raise ScoreArtifactError("threshold artifact requires a score ID and at least one policy")
        policies = tuple(threshold.policy for threshold in self.thresholds)
        if len(policies) != len(set(policies)):
            raise ScoreArtifactError("threshold artifact policies must be unique")
        if any(threshold.score_id != self.score_id for threshold in self.thresholds):
            raise ScoreArtifactError("threshold artifact policies must share one score ID")


def compute_b1_shared_threshold(scores: AnchorScoreArtifact, *, q: float) -> AnchorThresholds:
    local = [benign_quantile(client.calibration_benign, q) for client in scores.clients if client.calibration_eligible]
    if not local:
        raise ScoreArtifactError("B1 requires at least one eligible benign calibration client")
    shared = sum(local) / len(local)
    return AnchorThresholds(
        policy=ThresholdPolicy.B1,
        score_id=scores.manifest.score_id,
        q=q,
        per_client=tuple((client.client_id, shared) for client in scores.clients),
        shared_threshold=shared,
    )
