import pytest
import torch

from tests.support.cuda_lane import skip_if_cuda_unavailable


@pytest.mark.cuda
def test_cuda_lane_runs_a_no_op_device_check() -> None:
    skip_if_cuda_unavailable()
    tensor = torch.zeros(1, device="cuda")
    assert tensor.sum().item() == pytest.approx(0.0)


def test_cuda_device_requirement_skips_cleanly_when_hardware_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    with pytest.raises(pytest.skip.Exception):
        skip_if_cuda_unavailable()
