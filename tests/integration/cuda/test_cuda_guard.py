import pytest

from datp_core.domain.experiments.identities import CellId
from datp_core.domain.learning.training import DeterminismLevel
from datp_core.domain.runtime.admissibility import GpuIndex
from datp_core.domain.runtime.policies import DevicePolicy, DeviceSpec, PipelineStage
from datp_core.infrastructure.runtime.cuda import TorchCudaGuard
from tests.support.cuda_lane import skip_if_cuda_unavailable


@pytest.mark.cuda
def test_cuda_guard_assigns_the_visible_synthetic_cuda_device() -> None:
    skip_if_cuda_unavailable()
    guard = TorchCudaGuard(
        stage=PipelineStage.CALIBRATION_SCORE,
        cell_id=CellId(value="E-C1#0123456789abcdef"),
        determinism=DeterminismLevel.STRICT,
    )

    assignment = guard.require_cuda(DeviceSpec(policy=DevicePolicy.CUDA_REQUIRED, gpu_index=GpuIndex(value=0)))

    assert assignment.stage is PipelineStage.CALIBRATION_SCORE
    assert assignment.gpu_index == GpuIndex(value=0)
