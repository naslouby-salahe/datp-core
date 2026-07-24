"""Result records for resource-cost and alert-burden analyses."""

from __future__ import annotations

from attrs import define


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostEvaluationResult:
    evaluation: str
    transmitted_field_list: tuple[str, ...]
    estimated_threshold_message_bytes: int
    estimated_model_exchange_bytes_per_round: int
    estimated_checkpoint_storage_bytes: int


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostSeedResult:
    seed: int
    evaluations: tuple[ResourceCostEvaluationResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class ResourceCostAnalysisResult:
    analysis_label: str
    estimate_basis: str
    produced_fields: tuple[str, ...]
    seed_results: tuple[ResourceCostSeedResult, ...]


@define(frozen=True, slots=True, kw_only=True)
class AlertBurdenAnalysisResult:
    analysis_label: str
    formula: str
    status: str
    reason: str
    alerts_per_client_per_day: float | None = None
    benign_decision_rate_source: str | None = None


__all__ = [
    "AlertBurdenAnalysisResult",
    "ResourceCostAnalysisResult",
    "ResourceCostEvaluationResult",
    "ResourceCostSeedResult",
]
