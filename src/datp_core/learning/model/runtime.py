"""Deterministic CUDA runtime and seed derivation."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass

import numpy as np
import torch
from pydantic import BaseModel, ConfigDict, NonNegativeInt, PositiveInt

from datp_core.core.seeding import Seed, derive_seed
from datp_core.learning.contracts.enums import (
    CublasWorkspaceConfiguration,
    CudnnBenchmarkPolicy,
    DevicePolicy,
    PrecisionKind,
)
from datp_core.learning.contracts.model import IdentifierText


class SeedNamespaceProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    identifier: IdentifierText
    key: IdentifierText


class SeedDerivationProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    digest_bytes: PositiveInt
    model_initialization: SeedNamespaceProfile
    global_dataloader_shuffle: SeedNamespaceProfile
    personalized_dataloader_shuffle: SeedNamespaceProfile
    worker_initialization: SeedNamespaceProfile


class TorchRuntimeProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    device_policy: DevicePolicy
    cuda_device_index: NonNegativeInt
    deterministic_algorithms: bool
    warn_only_determinism: bool
    cudnn_benchmark: CudnnBenchmarkPolicy
    cublas_workspace_configuration: CublasWorkspaceConfiguration


@dataclass(frozen=True, slots=True)
class TorchRuntime:
    device: torch.device
    dtype: torch.dtype
    deterministic_algorithms: bool


@dataclass(frozen=True, slots=True)
class SeedComponent:
    name: str
    value: int | str


@dataclass(frozen=True, slots=True)
class WorkerSeeder:
    base_seed: int

    def __call__(self, worker_id: int) -> None:
        worker_seed = self.base_seed + worker_id
        random.seed(worker_seed)
        np.random.seed(worker_seed % (2**32))
        torch.manual_seed(worker_seed)


def create_runtime(profile: TorchRuntimeProfile, precision: PrecisionKind) -> TorchRuntime:
    if profile.device_policy is not DevicePolicy.CUDA_REQUIRED:
        raise ValueError("Learning runtime requires the CUDA-required device policy")
    if not torch.cuda.is_available():
        raise RuntimeError("Configured CUDA-required learning cannot run because CUDA is unavailable")
    if int(profile.cuda_device_index) >= torch.cuda.device_count():
        raise RuntimeError("Configured CUDA device index is unavailable")
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = profile.cublas_workspace_configuration.value
    torch.use_deterministic_algorithms(
        profile.deterministic_algorithms,
        warn_only=profile.warn_only_determinism,
    )
    torch.backends.cudnn.deterministic = profile.deterministic_algorithms
    torch.backends.cudnn.benchmark = profile.cudnn_benchmark is not CudnnBenchmarkPolicy.DISABLED
    dtype = precision_to_dtype(precision)
    return TorchRuntime(
        device=torch.device("cuda", int(profile.cuda_device_index)),
        dtype=dtype,
        deterministic_algorithms=profile.deterministic_algorithms,
    )


def precision_to_dtype(precision: PrecisionKind) -> torch.dtype:
    match precision:
        case PrecisionKind.FLOAT32:
            return torch.float32
        case PrecisionKind.FLOAT64:
            return torch.float64
    raise ValueError(f"Unsupported precision '{precision.value}'")


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed % (2**32))
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def derive_execution_seed(
    namespace: SeedNamespaceProfile,
    digest_bytes: int,
    components: tuple[SeedComponent, ...],
) -> Seed:
    return Seed(
        derive_seed(
            namespace.key,
            digest_bytes,
            tuple((component.name, component.value) for component in components),
        )
    )


def create_generator(seed: int) -> torch.Generator:
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return generator
