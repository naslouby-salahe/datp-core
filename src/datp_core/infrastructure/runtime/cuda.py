from dataclasses import dataclass

import torch

from datp_core.domain.errors import CudaDeviceMismatchError, CudaUnavailableError, InvalidCpuFallbackError
from datp_core.domain.experiments.identities import CellId
from datp_core.domain.learning.training import DeterminismLevel
from datp_core.domain.runtime.admissibility import GpuIndex
from datp_core.domain.runtime.policies import DevicePolicy, DeviceSpec, GpuAssignment, PipelineStage
from datp_core.infrastructure.runtime.determinism import configure_determinism


@dataclass(frozen=True, slots=True, kw_only=True)
class TorchCudaGuard:
    stage: PipelineStage
    cell_id: CellId
    determinism: DeterminismLevel

    def require_cuda(self, device: DeviceSpec) -> GpuAssignment:
        self._require_cuda_policy(device)
        gpu_index = self._require_visible_gpu(device)
        self._select_gpu(gpu_index.value)
        configure_determinism(self.determinism)
        return GpuAssignment(stage=self.stage, cell_id=self.cell_id, gpu_index=gpu_index)

    def _require_cuda_policy(self, device: DeviceSpec) -> None:
        if device.policy is not DevicePolicy.CUDA_REQUIRED:
            raise InvalidCpuFallbackError(
                detail="a CUDA guard cannot authorize a CPU-allowed device for a CUDA-required stage",
                stage=self.stage.value,
                policy=device.policy.value,
            )

    def _require_visible_gpu(self, device: DeviceSpec) -> GpuIndex:
        if not torch.cuda.is_available():
            raise CudaUnavailableError(
                detail="the requested CUDA device is unavailable; no CPU fallback is permitted",
                required_stage=self.stage.value,
            )
        gpu_index = device.gpu_index
        if gpu_index is None or gpu_index.value >= torch.cuda.device_count():
            raise CudaDeviceMismatchError(
                detail="the requested CUDA device index is not visible to this host",
                expected_device=repr(gpu_index),
                actual_device=f"gpu_count={torch.cuda.device_count()}",
            )
        return gpu_index

    def _select_gpu(self, expected_index: int) -> None:
        try:
            torch.cuda.set_device(expected_index)
            actual_index = torch.cuda.current_device()
        except RuntimeError as error:
            raise CudaDeviceMismatchError(
                detail="CUDA could not select the requested device index",
                expected_device=str(expected_index),
                actual_device="unavailable",
            ) from error
        if actual_index != expected_index:
            raise CudaDeviceMismatchError(
                detail="CUDA selected a device other than the requested index",
                expected_device=str(expected_index),
                actual_device=str(actual_index),
            )
