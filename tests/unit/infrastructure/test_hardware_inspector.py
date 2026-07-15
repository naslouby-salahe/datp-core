import builtins
from collections.abc import Mapping, Sequence
from inspect import signature
from types import ModuleType

import pytest
import torch

from datp_core.application.ports.runtime import HardwareInspector
from datp_core.infrastructure.runtime.hardware import TorchHardwareInspector


def test_hardware_inspector_matches_the_runtime_port() -> None:
    assert signature(TorchHardwareInspector.inspect) == signature(HardwareInspector.inspect)


def test_no_cuda_returns_a_complete_non_raising_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    inventory = TorchHardwareInspector().inspect()

    assert not inventory.cuda_available
    assert inventory.gpu_count == 0
    assert inventory.gpu_name is None
    assert inventory.vram_bytes is None
    assert inventory.torch_version == torch.__version__


def test_optional_library_failures_degrade_to_standard_library_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    import psutil
    import pynvml

    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(psutil, "virtual_memory", _failing_memory)
    monkeypatch.setattr(pynvml, "nvmlInit", _failing_nvml_initialization)

    inventory = TorchHardwareInspector().inspect()

    assert not inventory.cuda_available
    assert inventory.ram_bytes is None or inventory.ram_bytes > 0
    assert inventory.driver_version is None


def test_missing_optional_libraries_degrade_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def absent_optional_library(
        name: str,
        globals: Mapping[str, object] | None = None,
        locals: Mapping[str, object] | None = None,
        fromlist: Sequence[str] = (),
        level: int = 0,
    ) -> ModuleType:
        if name in {"psutil", "pynvml"}:
            raise ImportError(f"{name} unavailable")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", absent_optional_library)
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)

    inventory = TorchHardwareInspector().inspect()

    assert not inventory.cuda_available
    assert inventory.ram_bytes is None or inventory.ram_bytes > 0
    assert inventory.driver_version is None


def _failing_memory() -> object:
    raise RuntimeError("optional memory provider unavailable")


def _failing_nvml_initialization() -> None:
    import pynvml

    raise pynvml.NVMLError(1)
