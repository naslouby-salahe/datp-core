"""Low-level RNG seeding primitives (Python stdlib random + NumPy)."""

from __future__ import annotations

import random as _random

import numpy as np


def seed_python_random(seed: int) -> None:
    _random.seed(seed)


def seed_numpy_global(seed: int) -> None:
    np.random.seed(seed)


def make_numpy_generator(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)
