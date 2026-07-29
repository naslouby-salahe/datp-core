"""CUDA device resolution and compute provenance for GPU-appropriate work."""

from dataclasses import dataclass

import torch

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ExecutionStateError
from datp_core.domain.values import WorkerCount
from datp_core.protocols.runtime import CANONICAL_RUNTIME


@dataclass(frozen=True, slots=True)
class CudaProvenance:
    cuda_available: bool
    device_count: int
    device_name: str | None
    cuda_version: str | None
    torch_version: str


def require_cuda_available() -> None:
    if not CANONICAL_RUNTIME.require_cuda:
        raise ExecutionStateError(
            "canonical runtime requires CUDA but require_cuda is false",
            subject=ContractSubject.RUNTIME,
        )
    if not torch.cuda.is_available():
        raise ExecutionStateError(
            "CUDA is mandatory for GPU-appropriate operations and is unavailable",
            subject=ContractSubject.CUDA,
        )


def resolve_cuda_device() -> torch.device:
    """Return the canonical CUDA device. Never falls back to CPU."""
    require_cuda_available()
    return torch.device("cuda")


def canonical_worker_count() -> WorkerCount:
    """Maximum concurrency for suitable CPU-side independent work."""
    return CANONICAL_RUNTIME.worker_count


def cuda_provenance() -> CudaProvenance:
    available = torch.cuda.is_available()
    device_count = torch.cuda.device_count() if available else 0
    device_name = torch.cuda.get_device_name(0) if available and device_count > 0 else None
    cuda_version = torch.version.cuda if available else None
    return CudaProvenance(
        cuda_available=available,
        device_count=device_count,
        device_name=device_name,
        cuda_version=cuda_version,
        torch_version=torch.__version__,
    )
