"""Paired B1/B2 per-seed aggregation without cross-seed averaging."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class AnchorSeedSummary:
    seed: int
    checkpoint_id: str
    b1_cv_fpr: float
    b2_cv_fpr: float

    def __post_init__(self) -> None:
        if self.seed < 0:
            raise ValueError("anchor summary seed must not be negative")
        if not self.checkpoint_id:
            raise ValueError("anchor summary requires a frozen checkpoint ID")
        if not isfinite(self.b1_cv_fpr) or not isfinite(self.b2_cv_fpr):
            raise ValueError("anchor summary CV(FPR) values must be finite")
        if self.b1_cv_fpr < 0.0 or self.b2_cv_fpr < 0.0:
            raise ValueError("anchor summary CV(FPR) values must not be negative")

    @property
    def delta_cv_fpr(self) -> float:
        return self.b1_cv_fpr - self.b2_cv_fpr


def paired_anchor_summary(
    seed: int,
    b1_checkpoint_id: str,
    b2_checkpoint_id: str,
    b1_cv_fpr: float,
    b2_cv_fpr: float,
) -> AnchorSeedSummary:
    if b1_checkpoint_id != b2_checkpoint_id:
        raise ValueError("B1 and B2 must share the same frozen checkpoint within a seed")
    return AnchorSeedSummary(
        seed=seed,
        checkpoint_id=b1_checkpoint_id,
        b1_cv_fpr=b1_cv_fpr,
        b2_cv_fpr=b2_cv_fpr,
    )
