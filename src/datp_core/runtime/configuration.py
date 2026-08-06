"""Executable repository layout and runtime limits."""

from dataclasses import dataclass
from os import cpu_count
from pathlib import Path

from datp_core.domain.values.base import NonNegativeIntegerValue
from datp_core.domain.values.counts import WorkerCount


class CudaDeviceIndex(NonNegativeIntegerValue):
    validation_name = "CUDA device index"


@dataclass(frozen=True, slots=True, kw_only=True)
class RepositoryLayout:
    data_root: Path
    outputs_root: Path
    results_root: Path

    def __post_init__(self) -> None:
        roots = (self.data_root, self.outputs_root, self.results_root)
        if any(root.is_absolute() or not root.parts for root in roots):
            raise ValueError("repository roots must be non-empty project-relative paths")
        if len(set(roots)) != len(roots):
            raise ValueError("repository roots must be distinct")


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeConfiguration:
    layout: RepositoryLayout
    worker_count: WorkerCount
    cuda_device_index: CudaDeviceIndex


def _available_worker_count() -> WorkerCount:
    return WorkerCount(cpu_count() or 1)


CANONICAL_RUNTIME = RuntimeConfiguration(
    layout=RepositoryLayout(
        data_root=Path("data"),
        outputs_root=Path("outputs"),
        results_root=Path("results"),
    ),
    worker_count=_available_worker_count(),
    cuda_device_index=CudaDeviceIndex(0),
)

DATA_ROOT = CANONICAL_RUNTIME.layout.data_root
OUTPUTS_ROOT = CANONICAL_RUNTIME.layout.outputs_root
RESULTS_ROOT = CANONICAL_RUNTIME.layout.results_root
