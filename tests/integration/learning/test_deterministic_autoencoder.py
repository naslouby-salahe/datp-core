from hashlib import sha256
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.training import DeterminismLevel
from datp_core.domain.runtime.admissibility import WorkerCount
from datp_core.domain.runtime.seeds import DataLoaderSeedPlan, Seed
from datp_core.infrastructure.learning.models.autoencoder import build_fixed_autoencoder
from datp_core.infrastructure.runtime.determinism import build_dataloader_determinism, configure_determinism
from datp_core.infrastructure.runtime.processes import cuda_spawn_context


def _seed_plan(worker_count: int) -> DataLoaderSeedPlan:
    return DataLoaderSeedPlan(
        shuffle_seed=Seed(value=11),
        sampler_seed=Seed(value=12),
        worker_seed=Seed(value=13),
        client_seed=Seed(value=14),
        epoch_seed=Seed(value=15),
        round_seed=Seed(value=16),
        worker_count=WorkerCount(value=worker_count),
    )


def _row_order_checksum(worker_count: int) -> str:
    components = build_dataloader_determinism(_seed_plan(worker_count))
    dataset = TensorDataset(torch.arange(16, dtype=torch.float32).reshape(8, 2))
    if worker_count == 0:
        loader = DataLoader(
            dataset,
            batch_size=2,
            shuffle=True,
            generator=components.generator,
            num_workers=worker_count,
            worker_init_fn=components.worker_init_fn,
        )
    else:
        loader = DataLoader(
            dataset,
            batch_size=2,
            shuffle=True,
            generator=components.generator,
            num_workers=worker_count,
            worker_init_fn=components.worker_init_fn,
            multiprocessing_context=cuda_spawn_context(),
        )
    row_order = tuple(int(value) for batch in loader for value in batch[0][:, 0])
    return sha256(repr(row_order).encode()).hexdigest()


def test_fixed_autoencoder_is_seeded_and_has_no_batch_normalization() -> None:
    specification = AutoencoderSpec(
        input_dim=4,
        hidden_dims=(80, 40),
        bottleneck_dim=20,
        activation=ActivationFunction.RELU,
    )
    first = build_fixed_autoencoder(specification=specification, initialization_seed=Seed(value=17))
    second = build_fixed_autoencoder(specification=specification, initialization_seed=Seed(value=17))
    third = build_fixed_autoencoder(specification=specification, initialization_seed=Seed(value=18))

    batch_normalization_types = (nn.BatchNorm1d, nn.BatchNorm2d, nn.BatchNorm3d, nn.SyncBatchNorm)
    assert not any(isinstance(module, batch_normalization_types) for module in first.modules())
    assert torch.equal(first(torch.ones(2, 4)), second(torch.ones(2, 4)))
    assert not torch.equal(first(torch.ones(2, 4)), third(torch.ones(2, 4)))


def test_worker_count_parallelism_and_recreated_run_preserve_synthetic_row_order() -> None:
    configure_determinism(DeterminismLevel.STRICT)

    sequential_checksum = _row_order_checksum(0)
    parallel_checksum = _row_order_checksum(2)

    assert sequential_checksum == parallel_checksum
    assert parallel_checksum == _row_order_checksum(2)
    assert cuda_spawn_context().get_start_method() == "spawn"


def test_no_global_seed_call_exists_outside_the_worker_initializer() -> None:
    source_root = Path(__file__).parents[3] / "src" / "datp_core"
    source_paths = tuple(source_root.rglob("*.py"))
    offending_paths = tuple(
        path for path in source_paths if "torch.manual_seed" in path.read_text() and path.name != "determinism.py"
    )
    global_start_method_paths = tuple(path for path in source_paths if "set_start_method" in path.read_text())

    assert not offending_paths
    assert not global_start_method_paths
