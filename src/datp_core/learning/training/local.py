"""Deterministic local training and validation."""

from __future__ import annotations

from dataclasses import dataclass
import torch
from torch import nn
from torch.nn.utils import clip_grad_norm_, parameters_to_vector
from torch.optim import Adam, Optimizer
from torch.optim.lr_scheduler import LRScheduler, StepLR
from torch.utils.data import DataLoader, TensorDataset

from datp_core.learning.checkpoints.codec import ModelState, capture_model_state
from datp_core.learning.contracts.enums import (
    AccumulationRemainderPolicy,
    GradientClippingKind,
    IncompleteBatchPolicy,
    ReconstructionObjective,
    SchedulerKind,
    ShufflePolicy,
)
from datp_core.learning.contracts.model import (
    AdamOptimizerProfile,
    BatchingProfile,
    DenseAutoencoderProfile,
    GlobalNormGradientClippingProfile,
    StepSchedulerProfile,
)
from datp_core.learning.model.runtime import TorchRuntime, WorkerSeeder, create_generator


@dataclass(frozen=True, slots=True)
class LocalTrainingRequest:
    model: nn.Module
    training_tensor: torch.Tensor
    local_epochs: int
    epoch_seeds: tuple[int, ...]
    worker_seeds: tuple[int, ...]
    architecture: DenseAutoencoderProfile
    optimizer: AdamOptimizerProfile
    batching: BatchingProfile
    runtime: TorchRuntime
    proximal_reference: ModelState | None
    proximal_coefficient: float | None


@dataclass(frozen=True, slots=True)
class LocalTrainingResult:
    state: ModelState
    batch_count: int
    optimizer_step_count: int


def train_local_autoencoder(request: LocalTrainingRequest) -> LocalTrainingResult:
    _validate_request(request)
    model = request.model.to(device=request.runtime.device, dtype=request.runtime.dtype)
    model.train()
    optimizer = _build_optimizer(model, request.optimizer)
    scheduler = _build_scheduler(optimizer, request.optimizer)
    criterion = _build_loss(request.architecture)
    dataset = TensorDataset(request.training_tensor.to(dtype=request.runtime.dtype, device="cpu"))
    reference_vector = _reference_vector(model, request.proximal_reference, request.runtime)
    batch_count = 0
    optimizer_step_count = 0

    for epoch_index, (epoch_seed, worker_seed) in enumerate(
        zip(request.epoch_seeds, request.worker_seeds, strict=True)
    ):
        loader = _build_loader(dataset, request.batching, epoch_seed, worker_seed)
        optimizer.zero_grad(set_to_none=True)
        batches_since_step = 0
        epoch_batch_count = 0
        for (batch_inputs,) in loader:
            epoch_batch_count += 1
            batch_count += 1
            batches_since_step += 1
            batch_inputs = batch_inputs.to(
                device=request.runtime.device,
                dtype=request.runtime.dtype,
                non_blocking=request.batching.pin_memory,
            )
            reconstruction = model(batch_inputs)
            loss = criterion(reconstruction, batch_inputs)
            if reference_vector is not None and request.proximal_coefficient is not None:
                loss = loss + _proximal_penalty(model, reference_vector, request.proximal_coefficient)
            scaled_loss = loss / int(request.batching.gradient_accumulation_steps)
            scaled_loss.backward()
            boundary = batches_since_step == int(request.batching.gradient_accumulation_steps)
            if boundary:
                _apply_gradient_clipping(model, request.optimizer)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
                optimizer_step_count += 1
                batches_since_step = 0
        if epoch_batch_count == 0:
            raise ValueError("Configured batching produced no local-training batches")
        if batches_since_step > 0:
            if request.batching.accumulation_remainder_policy is AccumulationRemainderPolicy.STEP_PARTIAL:
                _rescale_partial_gradients(
                    model,
                    int(request.batching.gradient_accumulation_steps),
                    batches_since_step,
                )
                _apply_gradient_clipping(model, request.optimizer)
                optimizer.step()
                optimizer_step_count += 1
            optimizer.zero_grad(set_to_none=True)
        if scheduler is not None:
            scheduler.step()
        if epoch_index + 1 > request.local_epochs:
            raise RuntimeError("Local epoch accounting exceeded the configured epoch count")

    return LocalTrainingResult(
        state=capture_model_state(model),
        batch_count=batch_count,
        optimizer_step_count=optimizer_step_count,
    )


def reconstruction_loss(
    model: nn.Module,
    data: torch.Tensor,
    architecture: DenseAutoencoderProfile,
    batching: BatchingProfile,
    runtime: TorchRuntime,
) -> float:
    if data.ndim != 2 or int(data.shape[0]) < 1:
        raise ValueError("Validation requires a non-empty two-dimensional tensor")
    model = model.to(device=runtime.device, dtype=runtime.dtype)
    model.eval()
    criterion = _build_loss(architecture)
    dataset = TensorDataset(data.to(dtype=runtime.dtype, device="cpu"))
    loader = DataLoader(
        dataset,
        batch_size=int(batching.micro_batch_size),
        shuffle=False,
        drop_last=False,
        num_workers=int(batching.worker_count),
        pin_memory=batching.pin_memory,
        persistent_workers=batching.persistent_workers,
    )
    weighted_loss = 0.0
    total_rows = 0
    with torch.inference_mode():
        for (batch_inputs,) in loader:
            batch_inputs = batch_inputs.to(
                device=runtime.device,
                dtype=runtime.dtype,
                non_blocking=batching.pin_memory,
            )
            loss = criterion(model(batch_inputs), batch_inputs)
            row_count = int(batch_inputs.shape[0])
            if architecture.reduction.value == "sum":
                weighted_loss += float(loss.detach().cpu().item())
            else:
                weighted_loss += row_count * float(loss.detach().cpu().item())
            total_rows += row_count
    if total_rows < 1:
        raise ValueError("Validation loader produced no rows")
    return weighted_loss / total_rows


def _validate_request(request: LocalTrainingRequest) -> None:
    if request.local_epochs < 1:
        raise ValueError("Local training requires positive local epochs")
    if request.training_tensor.ndim != 2 or int(request.training_tensor.shape[0]) < 1:
        raise ValueError("Local training requires a non-empty two-dimensional tensor")
    if len(request.epoch_seeds) != request.local_epochs:
        raise ValueError("Local training requires one dataloader seed per epoch")
    if len(request.worker_seeds) != request.local_epochs:
        raise ValueError("Local training requires one worker seed per epoch")
    if (request.proximal_reference is None) != (request.proximal_coefficient is None):
        raise ValueError("Proximal state and coefficient must be provided together")
    if request.proximal_coefficient is not None and request.proximal_coefficient <= 0.0:
        raise ValueError("Proximal coefficient must be strictly positive")


def _build_loader(
    dataset: TensorDataset,
    batching: BatchingProfile,
    epoch_seed: int,
    worker_seed: int,
) -> DataLoader[tuple[torch.Tensor]]:
    shuffle = batching.shuffle_policy is ShufflePolicy.EACH_EPOCH
    drop_last = batching.incomplete_batch_policy is IncompleteBatchPolicy.DROP
    return DataLoader(
        dataset,
        batch_size=int(batching.micro_batch_size),
        shuffle=shuffle,
        drop_last=drop_last,
        num_workers=int(batching.worker_count),
        pin_memory=batching.pin_memory,
        persistent_workers=batching.persistent_workers,
        generator=create_generator(epoch_seed),
        worker_init_fn=WorkerSeeder(worker_seed),
    )


def _build_optimizer(model: nn.Module, profile: AdamOptimizerProfile) -> Optimizer:
    return Adam(
        model.parameters(),
        lr=float(profile.learning_rate),
        betas=(float(profile.beta_1), float(profile.beta_2)),
        eps=float(profile.epsilon),
        weight_decay=float(profile.weight_decay),
        amsgrad=profile.amsgrad,
    )


def _build_scheduler(optimizer: Optimizer, profile: AdamOptimizerProfile) -> LRScheduler | None:
    match profile.scheduler.kind:
        case SchedulerKind.NONE:
            return None
        case SchedulerKind.STEP:
            scheduler = profile.scheduler
            if not isinstance(scheduler, StepSchedulerProfile):
                raise TypeError("Step scheduler profile has an invalid runtime type")
            return StepLR(
                optimizer,
                step_size=int(scheduler.step_size_epochs),
                gamma=float(scheduler.gamma),
            )
    raise ValueError(f"Unsupported scheduler '{profile.scheduler.kind.value}'")


def _build_loss(profile: DenseAutoencoderProfile) -> nn.Module:
    match profile.objective:
        case ReconstructionObjective.MEAN_SQUARED_ERROR:
            return nn.MSELoss(reduction=profile.reduction.value)
        case ReconstructionObjective.MEAN_ABSOLUTE_ERROR:
            return nn.L1Loss(reduction=profile.reduction.value)
        case ReconstructionObjective.HUBER:
            return nn.HuberLoss(reduction=profile.reduction.value)
    raise ValueError(f"Unsupported reconstruction objective '{profile.objective.value}'")


def _reference_vector(
    model: nn.Module,
    reference: ModelState | None,
    runtime: TorchRuntime,
) -> torch.Tensor | None:
    if reference is None:
        return None
    tensors = tuple(
        reference.parameter(name).to(device=runtime.device, dtype=runtime.dtype)
        for name, _ in model.named_parameters()
    )
    if not tensors:
        raise ValueError("Proximal training requires trainable model parameters")
    return parameters_to_vector(tensors).detach()


def _proximal_penalty(
    model: nn.Module,
    reference_vector: torch.Tensor,
    coefficient: float,
) -> torch.Tensor:
    current_vector = parameters_to_vector(tuple(model.parameters()))
    if current_vector.shape != reference_vector.shape:
        raise ValueError("Proximal reference vector does not match the local model")
    return (coefficient / 2.0) * torch.sum((current_vector - reference_vector) ** 2)


def _rescale_partial_gradients(model: nn.Module, accumulation_steps: int, partial_steps: int) -> None:
    scale = accumulation_steps / partial_steps
    for parameter in model.parameters():
        if parameter.grad is not None:
            parameter.grad.mul_(scale)


def _apply_gradient_clipping(model: nn.Module, profile: AdamOptimizerProfile) -> None:
    match profile.gradient_clipping.kind:
        case GradientClippingKind.NONE:
            return
        case GradientClippingKind.GLOBAL_NORM:
            clipping = profile.gradient_clipping
            if not isinstance(clipping, GlobalNormGradientClippingProfile):
                raise TypeError("Global-norm clipping profile has an invalid runtime type")
            clip_grad_norm_(model.parameters(), max_norm=float(clipping.maximum_norm))
            return
    raise ValueError(f"Unsupported gradient clipping '{profile.gradient_clipping.kind.value}'")
