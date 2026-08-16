from pathlib import Path

import pytest
import torch

from datp_core.core.numeric import Seed, SeedDerivationComponent
from datp_core.runtime.compute import LEARNING_DEVICE
from datp_core.runtime.configuration import RepositoryLayout
from datp_core.runtime.determinism import (
    configure_deterministic_execution,
    derive_worker_seed,
)


def test_learning_device_is_cpu_unconditionally() -> None:
    assert LEARNING_DEVICE.type == "cpu"
    assert LEARNING_DEVICE == torch.device("cpu")


def test_repository_layout_rejects_ambiguous_roots() -> None:
    with pytest.raises(ValueError, match="project-relative"):
        RepositoryLayout(data_root=Path("/data"), outputs_root=Path("outputs"), results_root=Path("results"))
    with pytest.raises(ValueError, match="distinct"):
        RepositoryLayout(data_root=Path("data"), outputs_root=Path("data"), results_root=Path("results"))


def test_deterministic_cpu_execution_and_worker_seed_derivation() -> None:
    seed = Seed(7)
    configure_deterministic_execution(seed)
    first = torch.rand(8)
    configure_deterministic_execution(seed)
    assert torch.equal(first, torch.rand(8))

    worker_a = derive_worker_seed(seed, SeedDerivationComponent(0))
    worker_b = derive_worker_seed(seed, SeedDerivationComponent(1))
    assert worker_a != worker_b
    assert derive_worker_seed(seed, SeedDerivationComponent(0)) == worker_a
    with pytest.raises(ValueError, match="seed derivation component"):
        SeedDerivationComponent(-1)
