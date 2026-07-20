"""Domain models for operating point evaluation, confusion matrices, and metrics."""

from __future__ import annotations

from dataclasses import dataclass

from .identifiers import ClientId, MetricId, ThresholdPolicyId


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientConfusionMatrix:
    client_id: ClientId
    true_positives: int
    false_positives: int
    true_negatives: int
    false_negatives: int

    def __post_init__(self) -> None:
        if any(v < 0 for v in (self.true_positives, self.false_positives, self.true_negatives, self.false_negatives)):
            raise ValueError("Confusion matrix counts must be non-negative")

    @property
    def false_positive_rate(self) -> float:
        total_negatives = self.false_positives + self.true_negatives
        if total_negatives == 0:
            return 0.0
        return self.false_positives / total_negatives

    @property
    def true_positive_rate(self) -> float:
        total_positives = self.true_positives + self.false_negatives
        if total_positives == 0:
            return 0.0
        return self.true_positives / total_positives


@dataclass(frozen=True, slots=True, kw_only=True)
class MetricResultRecord:
    metric_id: MetricId
    policy_id: ThresholdPolicyId
    client_id: ClientId | None
    value: float
