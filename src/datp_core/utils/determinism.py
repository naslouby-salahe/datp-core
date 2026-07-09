"""Seed application and determinism reporting (docs/protocol/seed_plan.md).

Never claims a determinism guarantee that was not actually verified: strict
mode fails clearly instead of silently trusting an unavailable backend.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Any

from datp_core.domain.seeds import SeedPlan, SeedRole

from .random import seed_numpy_global, seed_python_random

_ROLE_SEED_OFFSETS: dict[SeedRole, int] = {
    SeedRole.TRAIN: 0,
    SeedRole.ANALYSIS: 1_000_000,
    SeedRole.STRESS_TEST: 2_000_000,
}


class DeterminismError(RuntimeError):
    """Raised when strict determinism was requested but cannot be guaranteed."""


@dataclass(frozen=True)
class DeterminismReport:
    seed: int
    python_seeded: bool
    numpy_seeded: bool
    torch_available: bool
    torch_seeded: bool
    cuda_deterministic_guaranteed: bool
    strict_mode: bool


def seed_for_role(seed: int, role: SeedRole) -> int:
    """Derive a role-specific seed so train/analysis/stress-test streams never collide."""
    return seed + _ROLE_SEED_OFFSETS[role]


def apply_seed(seed: int, *, strict: bool = False) -> DeterminismReport:
    seed_python_random(seed)
    seed_numpy_global(seed)

    torch_available = importlib.util.find_spec("torch") is not None
    torch_seeded = False
    cuda_deterministic_guaranteed = False

    if torch_available:
        import torch  # pyright: ignore[reportMissingImports]

        torch.manual_seed(seed)
        torch_seeded = True
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
            try:
                torch.use_deterministic_algorithms(True)
                cuda_deterministic_guaranteed = True
            except RuntimeError:
                cuda_deterministic_guaranteed = False
        else:
            cuda_deterministic_guaranteed = True

    if strict and not (torch_available and cuda_deterministic_guaranteed):
        raise DeterminismError(
            "strict determinism requires PyTorch with guaranteed deterministic algorithms; "
            f"torch_available={torch_available}, "
            f"cuda_deterministic_guaranteed={cuda_deterministic_guaranteed}"
        )

    return DeterminismReport(
        seed=seed,
        python_seeded=True,
        numpy_seeded=True,
        torch_available=torch_available,
        torch_seeded=torch_seeded,
        cuda_deterministic_guaranteed=cuda_deterministic_guaranteed,
        strict_mode=strict,
    )


def seed_plan_to_dict(plan: SeedPlan) -> dict[str, Any]:
    return {"seeds": list(plan.seeds), "role": plan.role.value}


def seed_plan_from_dict(data: dict[str, Any]) -> SeedPlan:
    return SeedPlan(seeds=tuple(data["seeds"]), role=SeedRole(data["role"]))
