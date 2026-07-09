"""Configured CUDA autoencoder for the fixed Regime A anchor."""

from __future__ import annotations

import copy
from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from datp_core.utils.hardware import DeviceType


class AutoencoderError(ValueError):
    """Raised when the configured anchor autoencoder cannot run on CUDA."""


ARCHITECTURE_ID = "anchor_ae_linear_relu_v2"


@dataclass
class Autoencoder:
    input_dim: int
    hidden_dim: int
    device: DeviceType
    module: nn.Sequential
    architecture_id: str
    frozen: bool

    @classmethod
    def initialize(cls, input_dim: int, *, seed: int, hidden_dim: int, device: DeviceType) -> Autoencoder:
        if input_dim < 1 or hidden_dim < 1:
            raise AutoencoderError("input_dim and hidden_dim must be positive")
        if device is not DeviceType.CUDA:
            raise AutoencoderError("anchor autoencoder requires the configured CUDA device")
        if not torch.cuda.is_available():
            raise AutoencoderError("configured CUDA device is unavailable")
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
        module = nn.Sequential(nn.Linear(input_dim, hidden_dim), nn.ReLU(), nn.Linear(hidden_dim, input_dim)).to(
            device.value
        )
        return cls(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            device=device,
            module=module,
            architecture_id=ARCHITECTURE_ID,
            frozen=False,
        )

    def copy(self) -> Autoencoder:
        return Autoencoder(
            input_dim=self.input_dim,
            hidden_dim=self.hidden_dim,
            device=self.device,
            module=copy.deepcopy(self.module),
            architecture_id=self.architecture_id,
            frozen=self.frozen,
        )

    def reconstruct(self, inputs: np.ndarray) -> np.ndarray:
        if inputs.ndim != 2 or inputs.shape[1] != self.input_dim:
            raise AutoencoderError(f"expected inputs with shape (n, {self.input_dim}), got {inputs.shape}")
        with torch.no_grad():
            tensor = torch.as_tensor(np.array(inputs, dtype=np.float32, copy=True), device=self.device.value)
            return self.module(tensor).detach().cpu().numpy().astype(np.float64, copy=False)

    def reconstruction_loss(self, inputs: np.ndarray) -> float:
        reconstruction = self.reconstruct(inputs)
        return float(np.mean((reconstruction - inputs) ** 2))

    def train_epoch(self, inputs: np.ndarray, *, learning_rate: float, momentum: float, weight_decay: float) -> float:
        if self.frozen:
            raise AutoencoderError("frozen autoencoders cannot train")
        if learning_rate <= 0.0 or not len(inputs):
            raise AutoencoderError("training requires a positive learning rate and non-empty input")
        tensor = torch.as_tensor(np.array(inputs, dtype=np.float32, copy=True), device=self.device.value)
        optimizer = torch.optim.SGD(
            self.module.parameters(), learning_rate, momentum=momentum, weight_decay=weight_decay
        )
        optimizer.zero_grad(set_to_none=True)
        loss = torch.nn.functional.mse_loss(self.module(tensor), tensor)
        loss.backward()
        optimizer.step()
        return float(loss.detach().cpu().item())

    def numpy_parameters(self) -> tuple[ModelParameter, ...]:
        return tuple(
            ModelParameter(name=name, values=tensor.detach().cpu().numpy().copy())
            for name, tensor in self.module.state_dict().items()
        )

    def parameter_values(self, name: str) -> np.ndarray:
        for parameter in self.numpy_parameters():
            if parameter.name == name:
                return parameter.values
        raise AutoencoderError(f"autoencoder has no parameter {name!r}")

    def load_numpy_parameters(self, parameters: tuple[ModelParameter, ...]) -> None:
        expected = self.module.state_dict()
        expected_names = tuple(expected)
        received_names = tuple(parameter.name for parameter in parameters)
        if received_names != expected_names:
            raise AutoencoderError("autoencoder state has unexpected parameters")
        converted: dict[str, torch.Tensor] = {}
        for parameter, (name, tensor) in zip(parameters, expected.items(), strict=True):
            value = parameter.values
            if tuple(value.shape) != tuple(tensor.shape):
                raise AutoencoderError(f"autoencoder parameter {name} has unexpected shape {value.shape}")
            converted[name] = torch.as_tensor(np.array(value, copy=True), dtype=tensor.dtype, device=self.device.value)
        self.module.load_state_dict(converted)

    def freeze(self) -> None:
        self.frozen = True
        self.module.eval()
        for parameter in self.module.parameters():
            parameter.requires_grad_(False)


@dataclass(frozen=True)
class ModelParameter:
    name: str
    values: np.ndarray

    def __post_init__(self) -> None:
        self.values.setflags(write=False)


@dataclass(frozen=True)
class ModelSummary:
    architecture_id: str
    input_dim: int
    hidden_dim: int
    device: DeviceType
    parameter_count: int


def model_summary(model: Autoencoder) -> ModelSummary:
    return ModelSummary(
        architecture_id=model.architecture_id,
        input_dim=model.input_dim,
        hidden_dim=model.hidden_dim,
        device=model.device,
        parameter_count=sum(parameter.numel() for parameter in model.module.parameters()),
    )
