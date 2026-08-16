import random

import numpy as np
import torch

from datp_core.core.numeric import Seed, SeedDerivationComponent


def configure_deterministic_execution(seed: Seed) -> None:
    seed_value = seed.value
    random.seed(seed_value)
    np.random.seed(seed_value)
    torch.manual_seed(seed_value)
    torch.use_deterministic_algorithms(True)


def derive_worker_seed(base_seed: Seed, component: SeedDerivationComponent) -> Seed:
    derived = (base_seed.value * 1_000_003 + component.value * 97 + 17) % (2**31 - 1)
    return Seed(derived)
