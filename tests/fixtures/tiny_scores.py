"""Tiny deterministic reconstruction-error score fixture. Shape only, not a scientific result."""

from __future__ import annotations

import numpy as np

MAX_FIXTURE_SIZE = 32


def tiny_benign_scores(seed: int = 0, n: int = 20) -> np.ndarray:
    assert n <= MAX_FIXTURE_SIZE, "fixtures must stay tiny"
    rng = np.random.default_rng(seed)
    return rng.random(n)
