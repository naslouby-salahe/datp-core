from pathlib import Path

import pytest
import torch

from datp_core.core.numeric import Seed, SeedDerivationComponent
from datp_core.runtime.compute import (
    cuda_provenance,
    require_cuda_available,
    resolve_cuda_device,
)
from datp_core.runtime.configuration import CANONICAL_RUNTIME, CudaDeviceIndex, RepositoryLayout
from datp_core.runtime.determinism import (
    configure_deterministic_execution,
    derive_worker_seed,
    seed_torch_generators,
)


def test_canonical_runtime_owns_repository_layout_and_cuda_device_index() -> None:
    assert CANONICAL_RUNTIME.layout == RepositoryLayout(
        data_root=Path("data"),
        outputs_root=Path("outputs"),
        results_root=Path("results"),
    )
    assert CANONICAL_RUNTIME.cuda_device_index == CudaDeviceIndex(0)


def test_repository_layout_rejects_ambiguous_roots() -> None:
    with pytest.raises(ValueError, match="project-relative"):
        RepositoryLayout(data_root=Path("/data"), outputs_root=Path("outputs"), results_root=Path("results"))
    with pytest.raises(ValueError, match="distinct"):
        RepositoryLayout(data_root=Path("data"), outputs_root=Path("data"), results_root=Path("results"))


def test_cuda_device_resolution_never_falls_back_to_cpu() -> None:
    require_cuda_available()
    device = resolve_cuda_device()
    assert device.type == "cuda"
    provenance = cuda_provenance()
    assert provenance.cuda_available is True
    assert provenance.device_count.value >= 1
    assert provenance.device_name is not None
    assert provenance.torch_version


def test_deterministic_cuda_setup_and_worker_seed_derivation() -> None:
    seed = Seed(0)
    configure_deterministic_execution(seed)
    generator = seed_torch_generators(seed)
    assert generator.device.type == "cuda"
    worker_a = derive_worker_seed(seed, SeedDerivationComponent(0))
    worker_b = derive_worker_seed(seed, SeedDerivationComponent(1))
    assert worker_a != worker_b
    assert derive_worker_seed(seed, SeedDerivationComponent(0)) == worker_a
    with pytest.raises(ValueError, match="seed derivation component"):
        SeedDerivationComponent(-1)


def test_cuda_tensor_smoke() -> None:
    device = resolve_cuda_device()
    values = torch.ones(4, device=device)
    assert values.is_cuda
    assert float(values.sum().item()) == 4.0
