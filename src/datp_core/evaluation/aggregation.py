"""Paired B1/B2 per-seed aggregation without cross-seed averaging."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnchorSeedSummary:
    seed: int
    checkpoint_id: str
    b1_cv_fpr: float
    b2_cv_fpr: float

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
