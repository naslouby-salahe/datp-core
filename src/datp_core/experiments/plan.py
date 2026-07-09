"""Explicit paired Regime A run-cell planning; planning never executes training."""

from __future__ import annotations

from dataclasses import dataclass

from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime
from datp_core.domain.seeds import CONFIRMATORY_SEEDS


class AnchorPlanError(ValueError):
    """Raised when a confirmatory anchor plan violates its fixed dimensions."""


@dataclass(frozen=True)
class AnchorRunCell:
    dataset_id: DatasetId
    regime: Regime
    training_algorithm: TrainingAlgorithm
    policy: ThresholdPolicy
    seed: int
    q: float


def confirmatory_anchor_plan(*, seeds: tuple[int, ...], q: float) -> tuple[AnchorRunCell, ...]:
    if seeds != CONFIRMATORY_SEEDS:
        raise AnchorPlanError("the confirmatory Regime A plan requires the locked 10-seed plan")
    if not 0.0 < q < 1.0:
        raise AnchorPlanError("the confirmatory Regime A plan requires a configured valid quantile")
    return tuple(
        AnchorRunCell(
            dataset_id=DatasetId.N_BAIOT,
            regime=Regime.A,
            training_algorithm=TrainingAlgorithm.FEDAVG,
            policy=policy,
            seed=seed,
            q=q,
        )
        for seed in seeds
        for policy in (ThresholdPolicy.B1, ThresholdPolicy.B2)
    )
