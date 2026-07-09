import importlib.util

import numpy as np
import pytest

from datp_core.domain.seeds import SeedPlan, SeedRole
from datp_core.utils.determinism import (
    DeterminismError,
    apply_seed,
    seed_for_role,
    seed_plan_from_dict,
    seed_plan_to_dict,
)

TORCH_AVAILABLE = importlib.util.find_spec("torch") is not None


def test_same_seed_gives_same_numpy_sequence():
    a = np.random.default_rng(42).random(5)
    b = np.random.default_rng(42).random(5)
    assert np.array_equal(a, b)


def test_different_seeds_differ():
    a = np.random.default_rng(1).random(5)
    b = np.random.default_rng(2).random(5)
    assert not np.array_equal(a, b)


def test_numpy_global_seed_is_reproducible():
    np.random.seed(7)
    first = np.random.random(3)
    np.random.seed(7)
    second = np.random.random(3)
    assert np.array_equal(first, second)


def test_paired_seed_plan_stable():
    plan_a = SeedPlan(seeds=(0, 1, 2), role=SeedRole.ANALYSIS)
    plan_b = SeedPlan(seeds=(0, 1, 2), role=SeedRole.ANALYSIS)
    assert plan_a == plan_b


def test_seed_for_role_is_deterministic_and_role_distinct():
    assert seed_for_role(0, SeedRole.TRAIN) == seed_for_role(0, SeedRole.TRAIN)
    assert seed_for_role(0, SeedRole.TRAIN) != seed_for_role(0, SeedRole.ANALYSIS)
    assert seed_for_role(0, SeedRole.ANALYSIS) != seed_for_role(0, SeedRole.STRESS_TEST)


def test_apply_seed_non_strict_succeeds_without_torch():
    report = apply_seed(0, strict=False)
    assert report.python_seeded is True
    assert report.numpy_seeded is True
    assert report.torch_available == TORCH_AVAILABLE


@pytest.mark.skipif(TORCH_AVAILABLE, reason="strict-mode-without-torch case requires torch to be absent")
def test_strict_mode_fails_clearly_when_torch_unavailable():
    with pytest.raises(DeterminismError):
        apply_seed(0, strict=True)


def test_seed_plan_serializes_to_manifest_compatible_form():
    plan = SeedPlan(seeds=(0, 1, 2), role=SeedRole.TRAIN)
    data = seed_plan_to_dict(plan)
    assert data == {"seeds": [0, 1, 2], "role": "train"}
    restored = seed_plan_from_dict(data)
    assert restored == plan
