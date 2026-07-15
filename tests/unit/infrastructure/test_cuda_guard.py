from inspect import signature

import pytest
import torch

from datp_core.application.ports.runtime import CudaGuard
from datp_core.domain.errors import CudaDeviceMismatchError, CudaUnavailableError, InvalidCpuFallbackError
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.learning.training import DeterminismLevel
from datp_core.domain.runtime.admissibility import GpuIndex
from datp_core.domain.runtime.policies import DevicePolicy, DeviceSpec, PipelineStage
from datp_core.infrastructure.runtime.cuda import TorchCudaGuard


def _guard(*, determinism: DeterminismLevel = DeterminismLevel.STRICT) -> TorchCudaGuard:
    return TorchCudaGuard(
        stage=PipelineStage.CALIBRATION_SCORE,
        cell_id=CellId(value="E-C1#0123456789abcdef"),
        determinism=determinism,
    )


def _cuda_device(index: int = 0) -> DeviceSpec:
    return DeviceSpec(policy=DevicePolicy.CUDA_REQUIRED, gpu_index=GpuIndex(value=index))


def test_guard_matches_the_cuda_port_signature() -> None:
    assert signature(TorchCudaGuard.require_cuda) == signature(CudaGuard.require_cuda)


def test_cuda_unavailable_fails_loudly_without_setting_a_device(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    monkeypatch.setattr(torch.cuda, "set_device", _unexpected_device_selection)
    guard = _guard()
    device = _cuda_device()

    with pytest.raises(CudaUnavailableError, match="no CPU fallback"):
        guard.require_cuda(device)


def test_cpu_allowed_policy_is_rejected_as_an_invalid_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.cuda, "set_device", _unexpected_device_selection)
    guard = _guard()
    device = DeviceSpec(policy=DevicePolicy.CPU_ALLOWED, gpu_index=None)

    with pytest.raises(InvalidCpuFallbackError, match="CPU-allowed"):
        guard.require_cuda(device)


def test_unavailable_gpu_index_raises_a_typed_device_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(torch.cuda, "set_device", _unexpected_device_selection)
    guard = _guard()
    device = _cuda_device(index=1)

    with pytest.raises(CudaDeviceMismatchError, match="not visible"):
        guard.require_cuda(device)


def test_cuda_selection_failure_is_normalized_to_a_typed_device_mismatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 1)

    def failing_selection(index: int) -> None:
        raise RuntimeError(f"cannot select {index}")

    monkeypatch.setattr(torch.cuda, "set_device", failing_selection)
    guard = _guard()
    device = _cuda_device()

    with pytest.raises(CudaDeviceMismatchError, match="could not select"):
        guard.require_cuda(device)


def test_guard_selects_the_requested_gpu_and_applies_strict_determinism(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    selected_indices: list[int] = []
    configured_levels: list[DeterminismLevel] = []
    monkeypatch.setattr(torch.cuda, "is_available", lambda: True)
    monkeypatch.setattr(torch.cuda, "device_count", lambda: 1)
    monkeypatch.setattr(torch.cuda, "set_device", selected_indices.append)
    monkeypatch.setattr(torch.cuda, "current_device", lambda: 0)
    monkeypatch.setattr("datp_core.infrastructure.runtime.cuda.configure_determinism", configured_levels.append)

    assignment = _guard().require_cuda(_cuda_device())

    assert assignment.stage is PipelineStage.CALIBRATION_SCORE
    assert assignment.cell_id == CellId(value="E-C1#0123456789abcdef")
    assert assignment.gpu_index == GpuIndex(value=0)
    assert selected_indices == [0]
    assert configured_levels == [DeterminismLevel.STRICT]


def _unexpected_device_selection(index: int) -> None:
    raise AssertionError(f"device selection must not occur, received index {index}")
