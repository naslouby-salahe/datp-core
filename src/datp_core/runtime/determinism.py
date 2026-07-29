"""Deterministic Python, NumPy, and PyTorch seeding for scientific execution."""

import random

import numpy as np
import torch

from datp_core.domain.values import Seed
from datp_core.runtime.compute import require_cuda_available


def configure_deterministic_execution(seed: Seed) -> None:
    """Configure global deterministic algorithms and primary RNG streams."""
    require_cuda_available()
    seed_value = seed.value
    random.seed(seed_value)
    np.random.seed(seed_value)
    torch.manual_seed(seed_value)
    torch.cuda.manual_seed_all(seed_value)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def derive_worker_seed(base_seed: Seed, worker_id: int) -> Seed:
    """Derive a stable per-worker seed from a base scientific seed."""
    if worker_id < 0:
        raise ValueError("worker_id must be non-negative")
    # Distinct, deterministic derivation; keeps values in a stable positive int range.
    derived = (base_seed.value * 1_000_003 + worker_id * 97 + 17) % (2**31 - 1)
    return Seed(derived)


def seed_torch_generators(seed: Seed) -> torch.Generator:
    """Create a CUDA generator seeded for deterministic GPU work."""
    require_cuda_available()
    generator = torch.Generator(device="cuda")
    generator.manual_seed(seed.value)
    return generator
