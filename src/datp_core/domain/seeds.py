"""Seed plan types (docs/protocol/seed_plan.md). 10 seeds locked before any result is observed."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SeedRole(StrEnum):
    TRAIN = "train"
    ANALYSIS = "analysis"
    STRESS_TEST = "stress_test"


CONFIRMATORY_SEEDS: tuple[int, ...] = tuple(range(10))
PRELIMINARY_SEEDS: tuple[int, ...] = tuple(range(5))


class SeedPlanError(ValueError):
    pass


@dataclass(frozen=True)
class SeedPlan:
    seeds: tuple[int, ...]
    role: SeedRole

    def __post_init__(self) -> None:
        if not self.seeds:
            raise SeedPlanError("seed plan must not be empty")
        if len(set(self.seeds)) != len(self.seeds):
            raise SeedPlanError(f"seed plan contains duplicate seeds: {self.seeds}")
        if any(seed < 0 for seed in self.seeds):
            raise SeedPlanError(f"seed plan contains negative seeds: {self.seeds}")


def paired_delta_seeds(plan_a: SeedPlan, plan_b: SeedPlan) -> tuple[int, ...]:
    """Seeds valid for Delta_s = CV(FPR)[B1,s] - CV(FPR)[B2,s] (seed_plan.md pairing rule).

    Both plans must share the identical seed set; comparing across mismatched
    seed sets or unfrozen checkpoints is never a valid pairing.
    """
    if plan_a.seeds != plan_b.seeds:
        raise SeedPlanError("paired delta requires identical seed sets")
    return plan_a.seeds
