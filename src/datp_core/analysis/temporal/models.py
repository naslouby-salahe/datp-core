"""Result record for temporal-recovery analysis."""

from __future__ import annotations

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class TemporalRecoveryAnalysisResult:
    analysis_label: str
    metric: str
    static_reference_cv: tuple[float, ...]
    frozen_future_cv: tuple[float, ...]
    recalibrated_future_cv: tuple[float, ...]
    drift_excess: tuple[float, ...]
    recovered_amount: tuple[float, ...]
    recovery_ratio: tuple[float | None, ...]
    meaningful_degradation: bool
    drift_confidence_interval: tuple[float, float]
    outcome_band: str
    defined_recovery_ratio_seed_count: int
    mean_defined_recovery_ratio: float | None
    negative_recovery_policy: str
    chronology_unverifiable_policy: str


__all__ = ["TemporalRecoveryAnalysisResult"]
