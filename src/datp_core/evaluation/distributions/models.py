"""Distribution models: CDF points, threshold positions, tradeoff entries, variance terms."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CdfPoint(BaseModel):
    model_config = ConfigDict(frozen=True)
    score: float
    cumulative_probability: float


class ThresholdPositionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    threshold: float
    benign_cdf: float | None
    attack_cdf: float | None


class ClientScoreDistributionRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    per_client_benign_score_cdf: tuple[CdfPoint, ...]
    per_client_attack_score_cdf: tuple[CdfPoint, ...]
    per_client_threshold_position: ThresholdPositionRecord
    threshold: float
    false_positive_rate: float | None
    false_positive_rate_status: str
    true_positive_rate: float | None
    true_positive_rate_status: str
    balanced_accuracy: float | None
    balanced_accuracy_status: str
    macro_f1: float | None
    macro_f1_status: str


class ThresholdTradeoffEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    threshold_shift: float
    fpr_delta: float | None
    tpr_delta: float | None


class QuantileVarianceTerms(BaseModel):
    model_config = ConfigDict(frozen=True)
    within_term: float
    between_term: float
    between_ratio: float | None
