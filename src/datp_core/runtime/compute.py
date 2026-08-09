"""CUDA device resolution and compute provenance for GPU-appropriate work."""

from dataclasses import dataclass

import torch

from datp_core.core.errors import (
    ErrorMessage,
    ExecutionStateError,
)
from datp_core.core.identifiers import ContractSubject, CudaDeviceName
from datp_core.core.numeric import CudaDeviceCount
from datp_core.runtime.configuration import CANONICAL_RUNTIME, CudaDeviceIndex


@dataclass(frozen=True, slots=True)
class CudaProvenance:
    cuda_available: bool
    device_count: CudaDeviceCount
    device_index: CudaDeviceIndex | None
    device_name: CudaDeviceName | None
    cuda_version: (
        str | None
    )  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists
    torch_version: str  # TODO:should be a class. Check what already exists. Do not use primitives for this, use something else. Check what already exists

    def __post_init__(self) -> None:
        selected = self.device_index is not None and self.device_name is not None
        if self.cuda_available != (self.device_count.value > 0 and selected):
            raise ValueError("CUDA availability must match the recorded selected device")
        if self.device_index is not None and self.device_index.value >= self.device_count.value:
            raise ValueError("CUDA device index must reference an available device")
        if not self.torch_version:
            raise ValueError("CUDA provenance requires the PyTorch version")


def require_cuda_available() -> None:
    if not torch.cuda.is_available():
        raise ExecutionStateError(
            ErrorMessage("CUDA is mandatory for GPU-appropriate operations and is unavailable"),
            subject=ContractSubject.CUDA,
        )
    configured_cuda_device_index()


def configured_cuda_device_index() -> CudaDeviceIndex:
    index = CANONICAL_RUNTIME.cuda_device_index
    count = torch.cuda.device_count()
    if index.value >= count:
        raise ExecutionStateError(
            ErrorMessage(f"configured CUDA device index {index.value} is unavailable; detected {count} devices"),
            subject=ContractSubject.CUDA,
        )
    return index


def resolve_cuda_device() -> torch.device:
    require_cuda_available()
    return torch.device(f"cuda:{configured_cuda_device_index().value}")


def cuda_provenance() -> CudaProvenance:
    available = torch.cuda.is_available()
    device_count = CudaDeviceCount(torch.cuda.device_count() if available else 0)
    device_index = configured_cuda_device_index() if available else None
    device_name = CudaDeviceName(torch.cuda.get_device_name(device_index.value)) if device_index is not None else None
    cuda_version = torch.version.cuda if available else None
    return CudaProvenance(
        cuda_available=available,
        device_count=device_count,
        device_index=device_index,
        device_name=device_name,
        cuda_version=cuda_version,
        torch_version=torch.__version__,
    )
