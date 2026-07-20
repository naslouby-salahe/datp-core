"""Per-client operating-point metrics calculated before any aggregation."""

from __future__ import annotations

from ..kernel.ids import ClientId, RegistryId
from .domain import AvailableMetricValue, ClientMetricSet, MetricStatus, UnavailableMetricValue


def evaluate_client(
    client_id: ClientId, scores: tuple[float, ...], labels: tuple[bool, ...], threshold: float
) -> ClientMetricSet:
    if len(scores) != len(labels):
        raise ValueError("scores and labels must have equal length")
    benign = tuple(score for score, attack in zip(scores, labels, strict=True) if not attack)
    attacks = tuple(score for score, attack in zip(scores, labels, strict=True) if attack)
    values = (
        _rate("fpr", tuple(score >= threshold for score in benign), MetricStatus.UNAVAILABLE_MISSING_BENIGN_CLASS),
        _rate("tpr", tuple(score >= threshold for score in attacks), MetricStatus.UNAVAILABLE_MISSING_ATTACK_CLASS),
    )
    return ClientMetricSet(client_id=client_id, values=values)


def _rate(
    identifier: str, decisions: tuple[bool, ...], unavailable: MetricStatus
) -> AvailableMetricValue | UnavailableMetricValue:
    metric_id = RegistryId[object](identifier)
    if not decisions:
        return UnavailableMetricValue(metric_id=metric_id, status=unavailable, reason="required class is absent")
    return AvailableMetricValue(metric_id=metric_id, value=sum(decisions) / len(decisions), denominator=len(decisions))
