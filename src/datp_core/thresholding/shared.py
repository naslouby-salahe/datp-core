"""B1 shared threshold: arithmetic mean of eligible local benign p95 values."""

from __future__ import annotations

from dataclasses import dataclass

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

    def threshold_for(self, client_id: str) -> float:
        for known_client_id, threshold in self.per_client:
            if known_client_id == client_id:
                return threshold
        raise ScoreArtifactError(f"no threshold exists for client {client_id!r}")


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
