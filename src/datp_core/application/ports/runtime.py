from datetime import datetime
from typing import Protocol

from datp_core.domain.artifacts.provenance import CodeState, DependencyLockState, EnvironmentInventory
from datp_core.domain.runtime.policies import (
    DeviceSpec,
    GpuAssignment,
    HardwareInventory,
    ResourcePressureRequest,
    ResourcePressureSnapshot,
)


class HardwareInspector(Protocol):
    def inspect(self) -> HardwareInventory: ...


class CodeStateProvider(Protocol):
    def inspect(self) -> CodeState: ...


class DependencyLockStateProvider(Protocol):
    def inspect(self) -> DependencyLockState: ...


class EnvironmentInventoryProvider(Protocol):
    def inspect(self) -> EnvironmentInventory: ...


class Clock(Protocol):
    def now(self) -> datetime: ...


class CudaGuard(Protocol):
    def require_cuda(self, device: DeviceSpec) -> GpuAssignment: ...


class ResourcePressureMonitor(Protocol):
    def inspect(self, request: ResourcePressureRequest) -> ResourcePressureSnapshot: ...
