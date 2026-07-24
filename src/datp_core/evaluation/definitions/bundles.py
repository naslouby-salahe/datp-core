"""Metric bundle record."""

from __future__ import annotations

from attrs import define

from datp_core.core.identifiers import MetricBundleId


@define(frozen=True, slots=True, kw_only=True)
class MetricBundleRecord:
    identifier: MetricBundleId
    metrics: tuple[str, ...]
    cross_client_aggregation: str | None
    primary_dispersion_metric: str | None
    model_quality_control: str | None
    excludes_ineligible_clients: bool | None
    requires_attack_evaluable_clients: bool | None
