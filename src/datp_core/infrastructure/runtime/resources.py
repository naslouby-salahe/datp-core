from collections.abc import Iterable
from dataclasses import dataclass
from os import cpu_count, getloadavg
from typing import assert_never

import psutil
import torch

from datp_core.domain.runtime.policies import (
    PauseDecision,
    ResourcePressureLevel,
    ResourcePressureRequest,
    ResourcePressureSnapshot,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceUsageSample:
    ram_used_bytes: int
    vram_allocated_bytes: int | None
    vram_reserved_bytes: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ResourceUsageSummary:
    peak_ram_bytes: int
    peak_vram_allocated_bytes: int | None
    peak_vram_reserved_bytes: int | None
    elapsed_seconds: float


class SystemResourcePressureMonitor:
    def inspect(self, request: ResourcePressureRequest) -> ResourcePressureSnapshot:
        ram_fraction = psutil.virtual_memory().used / request.resource_budget.maximum_ram_bytes.value
        vram_fraction = _vram_fraction(request)
        load_fraction = _load_fraction()
        level = _pressure_level(
            ram_fraction=ram_fraction,
            vram_fraction=vram_fraction,
            load_fraction=load_fraction,
            request=request,
        )
        return ResourcePressureSnapshot(
            level=level,
            ram_usage_fraction=ram_fraction,
            vram_usage_fraction=vram_fraction,
            load_usage_fraction=load_fraction,
            recommended_action=_recommended_action(level=level, request=request),
        )


def summarize_resource_usage(
    *, samples: tuple[ResourceUsageSample, ...], elapsed_seconds: float
) -> ResourceUsageSummary:
    if not samples:
        return ResourceUsageSummary(
            peak_ram_bytes=0,
            peak_vram_allocated_bytes=None,
            peak_vram_reserved_bytes=None,
            elapsed_seconds=elapsed_seconds,
        )
    return ResourceUsageSummary(
        peak_ram_bytes=max(sample.ram_used_bytes for sample in samples),
        peak_vram_allocated_bytes=_peak_optional(sample.vram_allocated_bytes for sample in samples),
        peak_vram_reserved_bytes=_peak_optional(sample.vram_reserved_bytes for sample in samples),
        elapsed_seconds=elapsed_seconds,
    )


def _vram_fraction(request: ResourcePressureRequest) -> float | None:
    if not torch.cuda.is_available():
        return None
    return torch.cuda.memory_reserved() / request.resource_budget.maximum_vram_bytes.value


def _load_fraction() -> float:
    available_cpus = cpu_count()
    if available_cpus is None or available_cpus < 1:
        return 0.0
    return getloadavg()[0] / available_cpus


def _pressure_level(
    *,
    ram_fraction: float,
    vram_fraction: float | None,
    load_fraction: float,
    request: ResourcePressureRequest,
) -> ResourcePressureLevel:
    fractions = (ram_fraction, load_fraction) if vram_fraction is None else (ram_fraction, vram_fraction, load_fraction)
    if any(fraction >= 1.0 for fraction in fractions):
        return ResourcePressureLevel.CRITICAL
    thresholds = request.pressure_policy
    elevated = (
        ram_fraction >= thresholds.ram_pressure_fraction.value
        or load_fraction >= thresholds.load_pressure_fraction.value
        or (vram_fraction is not None and vram_fraction >= thresholds.vram_pressure_fraction.value)
    )
    return ResourcePressureLevel.ELEVATED if elevated else ResourcePressureLevel.NORMAL


def _recommended_action(*, level: ResourcePressureLevel, request: ResourcePressureRequest) -> PauseDecision:
    match level:
        case ResourcePressureLevel.NORMAL:
            return PauseDecision.CONTINUE
        case ResourcePressureLevel.ELEVATED:
            return request.pressure_policy.elevated_response
        case ResourcePressureLevel.CRITICAL:
            return request.pressure_policy.critical_response
        case _ as unreachable:
            assert_never(unreachable)


def _peak_optional(values: Iterable[int | None]) -> int | None:
    observed = tuple(value for value in values if value is not None)
    return max(observed) if observed else None
