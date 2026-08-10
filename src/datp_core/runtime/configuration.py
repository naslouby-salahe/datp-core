from dataclasses import dataclass
from pathlib import Path

from datp_core.core.numeric import NonNegativeIntegerValue


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
        if len(frozenset(roots)) != len(roots):
            raise ValueError("repository roots must be distinct")


@dataclass(frozen=True, slots=True, kw_only=True)
class RuntimeConfiguration:
    layout: RepositoryLayout
    cuda_device_index: CudaDeviceIndex


CANONICAL_RUNTIME = RuntimeConfiguration(
    layout=RepositoryLayout(
        data_root=Path("data"),
        outputs_root=Path("outputs"),
        results_root=Path("results"),
    ),
    cuda_device_index=CudaDeviceIndex(0),
)

DATA_ROOT = CANONICAL_RUNTIME.layout.data_root
OUTPUTS_ROOT = CANONICAL_RUNTIME.layout.outputs_root
RESULTS_ROOT = CANONICAL_RUNTIME.layout.results_root
