"""Placeholder tiny B-FedStatsBenign-style calibration score fixture for later phases.

Shape only, not a scientific result: the real pooled-variance + matched-
exceedance computation is Phase 4+ (docs/protocol/policies.md).
"""

from __future__ import annotations

import numpy as np


def tiny_fedstats_benign_calibration_scores(
    seed: int = 0, n_clients: int = 3, n_per_client: int = 10
) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    return {f"fixture-client-{i}": rng.random(n_per_client) for i in range(n_clients)}
