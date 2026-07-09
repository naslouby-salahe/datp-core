"""Device selection: CPU fallback by default, CUDA only when actually available.

Never assumes a GPU is present and never hardcodes local hardware; the caller
always gets back what was actually resolved, not what was hoped for.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

DEVICE_ENV_VAR = "DATP_DEVICE"


class DeviceType(StrEnum):
    CPU = "cpu"
    CUDA = "cuda"
    AUTO = "auto"


class HardwareError(RuntimeError):
    """Raised when the requested device cannot be honestly provided."""


@dataclass(frozen=True)
class DeviceDescriptor:
    requested: DeviceType
    resolved: DeviceType
    torch_available: bool
    cuda_available: bool
    vram_limit_mb: int | None = None


def _torch_available() -> bool:
    return importlib.util.find_spec("torch") is not None


def _cuda_available() -> bool:
    if not _torch_available():
        return False
    import torch  # pyright: ignore[reportMissingImports]

    return bool(torch.cuda.is_available())


def select_device(
    requested: DeviceType = DeviceType.AUTO,
    *,
    strict: bool = False,
    vram_limit_mb: int | None = None,
) -> DeviceDescriptor:
    torch_available = _torch_available()
    cuda_available = _cuda_available()

    if requested is DeviceType.CUDA:
        if not cuda_available:
            raise HardwareError("cuda device requested but no CUDA-capable accelerator is available")
        resolved = DeviceType.CUDA
    elif requested is DeviceType.CPU:
        resolved = DeviceType.CPU
    else:
        resolved = DeviceType.CUDA if cuda_available else DeviceType.CPU

    if strict and resolved is not DeviceType.CUDA:
        raise HardwareError(
            f"strict mode requires a CUDA accelerator; resolved device would be {resolved.value}"
        )

    return DeviceDescriptor(
        requested=requested,
        resolved=resolved,
        torch_available=torch_available,
        cuda_available=cuda_available,
        vram_limit_mb=vram_limit_mb,
    )


def select_device_from_env(
    env: dict[str, str] | None = None,
    *,
    strict: bool = False,
) -> DeviceDescriptor:
    env_map = os.environ if env is None else env
    requested = DeviceType(env_map.get(DEVICE_ENV_VAR) or DeviceType.AUTO)
    return select_device(requested, strict=strict)


def device_descriptor_to_dict(descriptor: DeviceDescriptor) -> dict[str, Any]:
    return {
        "requested": descriptor.requested.value,
        "resolved": descriptor.resolved.value,
        "torch_available": descriptor.torch_available,
        "cuda_available": descriptor.cuda_available,
        "vram_limit_mb": descriptor.vram_limit_mb,
    }
