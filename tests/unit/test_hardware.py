import pytest

from datp_core.utils.hardware import (
    DEVICE_ENV_VAR,
    DeviceType,
    HardwareError,
    device_descriptor_to_dict,
    select_device,
    select_device_from_env,
)


def test_auto_mode_selects_cuda_when_available():
    descriptor = select_device()
    assert descriptor.resolved is DeviceType.CUDA


def test_cuda_request_fails_clearly_when_unavailable(monkeypatch):
    monkeypatch.setattr("datp_core.utils.hardware._cuda_available", lambda: False)
    with pytest.raises(HardwareError):
        select_device(DeviceType.CUDA)


def test_auto_mode_returns_a_valid_device_descriptor():
    descriptor = select_device(DeviceType.AUTO)
    assert descriptor.resolved in (DeviceType.CPU, DeviceType.CUDA)
    assert descriptor.requested is DeviceType.AUTO


def test_strict_mode_rejects_unavailable_accelerator(monkeypatch):
    monkeypatch.setattr("datp_core.utils.hardware._cuda_available", lambda: False)
    with pytest.raises(HardwareError):
        select_device(DeviceType.AUTO, strict=True)


def test_explicit_cpu_request_never_raises_even_in_strict_mode_check():
    descriptor = select_device(DeviceType.CPU)
    assert descriptor.resolved is DeviceType.CPU


def test_device_descriptor_serializes_to_manifest_compatible_form():
    descriptor = select_device(DeviceType.CPU, vram_limit_mb=4096)
    data = device_descriptor_to_dict(descriptor)
    assert data == {
        "requested": "cpu",
        "resolved": "cpu",
        "torch_available": descriptor.torch_available,
        "cuda_available": descriptor.cuda_available,
        "vram_limit_mb": 4096,
    }


def test_select_device_from_env_reads_documented_variable():
    descriptor = select_device_from_env({DEVICE_ENV_VAR: "cpu"})
    assert descriptor.resolved is DeviceType.CPU
    assert descriptor.requested is DeviceType.CPU


def test_select_device_from_env_defaults_to_auto():
    descriptor = select_device_from_env({})
    assert descriptor.requested is DeviceType.AUTO
