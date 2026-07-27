"""Metric bundle record."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from datp_core.core.identifiers import MetricBundleId


class MetricBundleRecord(BaseModel):
    model_config = ConfigDict(frozen=True)

    identifier: MetricBundleId
    metrics: tuple[str, ...]
    cross_client_aggregation: str | None
    primary_dispersion_metric: str | None
    model_quality_control: str | None
    excludes_ineligible_clients: bool | None
    requires_attack_evaluable_clients: bool | None
