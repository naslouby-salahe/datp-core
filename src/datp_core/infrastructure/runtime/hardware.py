import os

import torch

from datp_core.domain.runtime.policies import HardwareInventory


class TorchHardwareInspector:
    def inspect(self) -> HardwareInventory:
        cuda_available = torch.cuda.is_available()
        gpu_count = torch.cuda.device_count() if cuda_available else 0
        gpu_name, vram_bytes = _gpu_details(cuda_available=cuda_available, gpu_count=gpu_count)
        return HardwareInventory(
            cuda_available=cuda_available,
            gpu_name=gpu_name,
            gpu_count=gpu_count,
            vram_bytes=vram_bytes,
            torch_version=torch.__version__,
            cuda_runtime=torch.version.cuda,
            driver_version=_driver_version(),
            cpu_count=os.cpu_count() or 0,
            ram_bytes=_ram_bytes(),
        )


def _gpu_details(*, cuda_available: bool, gpu_count: int) -> tuple[str | None, int | None]:
    if not cuda_available or gpu_count < 1:
        return None, None
    try:
        import pynvml
    except ImportError:
        return None, None
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        name = pynvml.nvmlDeviceGetName(handle)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        return (name.decode() if isinstance(name, bytes) else name), memory.total
    except pynvml.NVMLError:
        return None, None
    finally:
        try:
            pynvml.nvmlShutdown()
        except pynvml.NVMLError:
            pass


def _ram_bytes() -> int | None:
    try:
        import psutil
    except ImportError:
        return _stdlib_ram_bytes()
    try:
        return int(psutil.virtual_memory().total)
    except (AttributeError, OSError, RuntimeError):
        return _stdlib_ram_bytes()


def _stdlib_ram_bytes() -> int | None:
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
    except (AttributeError, OSError, ValueError):
        return None


def _driver_version() -> str | None:
    try:
        import pynvml
    except ImportError:
        return None
    try:
        pynvml.nvmlInit()
        value = pynvml.nvmlSystemGetDriverVersion()
        return value.decode() if isinstance(value, bytes) else value
    except pynvml.NVMLError:
        return None
    finally:
        try:
            pynvml.nvmlShutdown()
        except pynvml.NVMLError:
            pass
