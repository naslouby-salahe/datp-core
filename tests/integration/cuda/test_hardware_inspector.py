import pytest

from datp_core.infrastructure.runtime.hardware import TorchHardwareInspector
from tests.support.cuda_lane import skip_if_cuda_unavailable


@pytest.mark.cuda
def test_hardware_inventory_matches_the_visible_cuda_device() -> None:
    skip_if_cuda_unavailable()
    inventory = TorchHardwareInspector().inspect()

    assert inventory.cuda_available
    assert inventory.gpu_count >= 1
    assert inventory.gpu_name is not None
    assert inventory.vram_bytes is not None
    assert inventory.vram_bytes > 0
