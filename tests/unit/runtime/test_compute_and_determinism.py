import pytest
import torch

from datp_core.domain.values import Seed
from datp_core.protocols.runtime import CANONICAL_RUNTIME
from datp_core.runtime.compute import (
    canonical_worker_count,
    cuda_provenance,
    require_cuda_available,
    resolve_cuda_device,
)
from datp_core.runtime.determinism import (
    configure_deterministic_execution,
    derive_worker_seed,
    seed_torch_generators,
)


def test_canonical_runtime_requires_cuda_and_six_workers() -> None:
    assert CANONICAL_RUNTIME.require_cuda is True
    assert CANONICAL_RUNTIME.worker_count == 6
    assert canonical_worker_count() == 6


def test_cuda_device_resolution_never_falls_back_to_cpu() -> None:
    require_cuda_available()
    device = resolve_cuda_device()
    assert device.type == "cuda"
    provenance = cuda_provenance()
    assert provenance.cuda_available is True
    assert provenance.device_count >= 1
    assert provenance.device_name is not None
    assert provenance.torch_version


def test_deterministic_cuda_setup_and_worker_seed_derivation() -> None:
    seed = Seed(0)
    configure_deterministic_execution(seed)
    generator = seed_torch_generators(seed)
    assert generator.device.type == "cuda"
    worker_a = derive_worker_seed(seed, 0)
    worker_b = derive_worker_seed(seed, 1)
    assert worker_a != worker_b
    assert derive_worker_seed(seed, 0) == worker_a
    with pytest.raises(ValueError, match="non-negative"):
        derive_worker_seed(seed, -1)


def test_cuda_tensor_smoke() -> None:
    device = resolve_cuda_device()
    values = torch.ones(4, device=device)
    assert values.is_cuda
    assert float(values.sum().item()) == 4.0
