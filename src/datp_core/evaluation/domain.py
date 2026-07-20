"""Typed metric availability contracts."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ..kernel.ids import ClientId, RegistryId


class MetricStatus(StrEnum):
    AVAILABLE = "available"
    UNDEFINED_ZERO_DENOMINATOR = "undefined_zero_denominator"
    UNAVAILABLE_MISSING_BENIGN_CLASS = "unavailable_missing_benign_class"
    UNAVAILABLE_MISSING_ATTACK_CLASS = "unavailable_missing_attack_class"
    UNAVAILABLE_INVALID_ATTACK_ASSIGNMENT = "unavailable_invalid_attack_assignment"


@dataclass(frozen=True, slots=True, kw_only=True)
class AvailableMetricValue:
    metric_id: RegistryId[object]
    value: float
    denominator: int


@dataclass(frozen=True, slots=True, kw_only=True)
class UnavailableMetricValue:
    metric_id: RegistryId[object]
    status: MetricStatus
    reason: str


MetricValue = AvailableMetricValue | UnavailableMetricValue


@dataclass(frozen=True, slots=True, kw_only=True)
class ClientMetricSet:
    client_id: ClientId
    values: tuple[MetricValue, ...]
