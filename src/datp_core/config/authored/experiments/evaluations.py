"""Authored per-experiment evaluation specification (experiments.yaml ``evaluations``)."""

from __future__ import annotations

from pydantic import JsonValue

from datp_core.config.authored.base import StrictFrozenConfigModel


class EvaluationSpecConfig(StrictFrozenConfigModel):
    label: str
    threshold_policy: str
    overrides: dict[str, JsonValue] | None = None
    run_requirement: str | None = None
    population: str | None = None
    recalibration_mode: str | None = None
