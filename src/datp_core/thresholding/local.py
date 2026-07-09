"""B2 local threshold: per-client benign p95 with locked shared fallback."""

from __future__ import annotations

from datp_core.domain.policies import ThresholdPolicy
from datp_core.models.scoring import AnchorScoreArtifact, ScoreArtifactError
from datp_core.thresholding.quantiles import benign_quantile
from datp_core.thresholding.shared import AnchorThresholds


def compute_b2_local_threshold(scores: AnchorScoreArtifact, *, q: float) -> AnchorThresholds:
    eligible = tuple(
        (client.client_id, benign_quantile(client.calibration_benign, q))
        for client in scores.clients
        if client.calibration_eligible
    )
    if not eligible:
        raise ScoreArtifactError("B2 requires at least one eligible benign calibration client")
    shared_fallback = sum(threshold for _, threshold in eligible) / len(eligible)
    return AnchorThresholds(
        policy=ThresholdPolicy.B2,
        score_id=scores.manifest.score_id,
        q=q,
        per_client=tuple(
            (
                client.client_id,
                next(
                    (threshold for eligible_id, threshold in eligible if eligible_id == client.client_id),
                    shared_fallback,
                ),
            )
            for client in scores.clients
        ),
        shared_threshold=shared_fallback,
    )
