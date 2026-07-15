from inspect import signature

import pytest

from datp_core.application.ports.runtime import ResourcePressureMonitor
from datp_core.domain.runtime.admissibility import (
    DiskBudgetBytes,
    PrefetchCapacity,
    RamBudgetBytes,
    VramBudgetBytes,
    VramFraction,
    WorkerCount,
)
from datp_core.domain.runtime.policies import (
    PauseDecision,
    ResourceBudget,
    ResourcePressureLevel,
    ResourcePressurePolicy,
    ResourcePressureRequest,
)
from datp_core.infrastructure.runtime.resources import (
    ResourceUsageSample,
    SystemResourcePressureMonitor,
    summarize_resource_usage,
)


def _request() -> ResourcePressureRequest:
    return ResourcePressureRequest(
        resource_budget=ResourceBudget(
            maximum_ram_bytes=RamBudgetBytes(value=100),
            maximum_vram_bytes=VramBudgetBytes(value=100),
            maximum_worker_count=WorkerCount(value=1),
            maximum_prefetch_capacity=PrefetchCapacity(value=0),
            maximum_disk_bytes=DiskBudgetBytes(value=100),
            storage_safety_reserve=DiskBudgetBytes(value=1),
        ),
        pressure_policy=ResourcePressurePolicy(
            ram_pressure_fraction=VramFraction(value=0.7),
            vram_pressure_fraction=VramFraction(value=0.7),
            load_pressure_fraction=VramFraction(value=0.7),
            elevated_response=PauseDecision.PAUSE_AT_SAFE_BOUNDARY,
            critical_response=PauseDecision.EXIT_AFTER_RECOVERY_COMMIT,
        ),
    )


def test_monitor_matches_the_runtime_port() -> None:
    assert signature(SystemResourcePressureMonitor.inspect) == signature(ResourcePressureMonitor.inspect)


def test_elevated_pressure_recommends_only_a_closed_pause_decision(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Memory:
        used = 80

    monkeypatch.setattr("datp_core.infrastructure.runtime.resources.psutil.virtual_memory", lambda: _Memory())
    monkeypatch.setattr("datp_core.infrastructure.runtime.resources.torch.cuda.is_available", lambda: False)
    monkeypatch.setattr("datp_core.infrastructure.runtime.resources.getloadavg", lambda: (0.0, 0.0, 0.0))
    monkeypatch.setattr("datp_core.infrastructure.runtime.resources.cpu_count", lambda: 1)

    snapshot = SystemResourcePressureMonitor().inspect(_request())

    assert snapshot.level is ResourcePressureLevel.ELEVATED
    assert snapshot.recommended_action is PauseDecision.PAUSE_AT_SAFE_BOUNDARY


def test_usage_summary_uses_observed_peaks() -> None:
    summary = summarize_resource_usage(
        samples=(
            ResourceUsageSample(ram_used_bytes=4, vram_allocated_bytes=2, vram_reserved_bytes=3),
            ResourceUsageSample(ram_used_bytes=8, vram_allocated_bytes=1, vram_reserved_bytes=5),
        ),
        elapsed_seconds=2.5,
    )

    assert summary.peak_ram_bytes == 8
    assert summary.peak_vram_allocated_bytes == 2
    assert summary.peak_vram_reserved_bytes == 5
    assert summary.elapsed_seconds == 2.5
