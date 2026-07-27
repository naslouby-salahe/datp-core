"""Execution fingerprint projection and the execution fingerprint builder."""

from __future__ import annotations

from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from datp_core.config.resolution.runtime import ResolvedRuntimeConfiguration
from datp_core.core.hashing import Fingerprint


class ExecutionProjection(BaseModel):
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)
    scientific_fingerprint: str
    active_execution_profile: object
    determinism: object
    device_policy: object
    resource_pressure: object
    raw_source_policy: object


def build_execution_projection(
    *,
    scientific_fingerprint: Fingerprint,
    runtime: ResolvedRuntimeConfiguration,
    projection_module: Callable[[object], object],
) -> ExecutionProjection:
    return ExecutionProjection(
        scientific_fingerprint=scientific_fingerprint.value,
        active_execution_profile=projection_module(runtime.active_execution_profile),
        determinism=projection_module(runtime.determinism_enforcement),
        device_policy=projection_module(runtime.device_policy_rules),
        resource_pressure=projection_module(runtime.resource_pressure_policy),
        raw_source_policy=projection_module(runtime.raw_source_policy),
    )
