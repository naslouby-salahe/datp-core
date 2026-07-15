from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from random import seed as seed_python

import numpy as np
import torch

from datp_core.domain.learning.training import DeterminismLevel
from datp_core.domain.runtime.seeds import DataLoaderSeedPlan


@dataclass(frozen=True, slots=True, kw_only=True)
class DataLoaderDeterminism:
    generator: torch.Generator
    worker_init_fn: Callable[[int], None]


def configure_determinism(level: DeterminismLevel) -> None:
    if level is not DeterminismLevel.STRICT:
        return
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False


def build_dataloader_determinism(seed_plan: DataLoaderSeedPlan) -> DataLoaderDeterminism:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed_plan.shuffle_seed.value)
    return DataLoaderDeterminism(
        generator=generator,
        worker_init_fn=partial(initialize_dataloader_worker, seed_plan=seed_plan),
    )


def initialize_dataloader_worker(worker_index: int, *, seed_plan: DataLoaderSeedPlan) -> None:
    worker_seed = seed_plan.worker_seed_for(worker_index).value
    seed_python(worker_seed)
    np.random.seed(worker_seed % (2**32))
    torch.manual_seed(worker_seed)  # type: ignore[reportUnknownMemberType]  # PyTorch's stub omits the seed type.
