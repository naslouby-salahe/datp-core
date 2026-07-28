"""The sole mapping boundary for PyTorch and Safetensors model state."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import quote

import numpy as np
import torch
from numpy.typing import NDArray
from safetensors.torch import load as load_safetensors
from safetensors.torch import save as save_safetensors
from torch import nn

from datp_core.learning.contracts.enums import CheckpointStateKind


@dataclass(frozen=True, slots=True)
class TensorParameter:
    name: str
    tensor: torch.Tensor


@dataclass(frozen=True, slots=True)
class ModelState:
    parameters: tuple[TensorParameter, ...]

    def parameter(self, name: str) -> torch.Tensor:
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter.tensor
        raise ValueError(f"Model state has no parameter named '{name}'")


@dataclass(frozen=True, slots=True)
class CapturedCheckpoint:
    round_number: int
    state: ModelState


@dataclass(frozen=True, slots=True)
class ClientModelState:
    client_id: str
    state: ModelState


@dataclass(frozen=True, slots=True)
class PersonalizedCapturedCheckpoint:
    round_number: int
    global_state: ModelState
    client_states: tuple[ClientModelState, ...]


@dataclass(frozen=True, slots=True)
class CheckpointKey:
    round_number: int
    state_kind: CheckpointStateKind
    parameter_name: str
    client_id: str | None

    def render(self) -> str:
        if self.round_number < 1:
            raise ValueError("Checkpoint round must be positive")
        if self.state_kind is CheckpointStateKind.GLOBAL:
            if self.client_id is not None:
                raise ValueError("Global checkpoint key must not carry a client identifier")
            return f"round/{self.round_number}/global/{self.parameter_name}"
        if self.client_id is None:
            raise ValueError("Personalized checkpoint key requires a client identifier")
        return f"round/{self.round_number}/client/{quote(self.client_id, safe='')}/{self.parameter_name}"


def capture_model_state(model: nn.Module) -> ModelState:
    raw_state = model.state_dict()
    parameters = tuple(
        TensorParameter(name=name, tensor=tensor.detach().cpu().clone()) for name, tensor in raw_state.items()
    )
    _validate_state(parameters)
    return ModelState(parameters=parameters)


def load_model_state(model: nn.Module, state: ModelState) -> None:
    _validate_state(state.parameters)
    mapping = {parameter.name: parameter.tensor for parameter in state.parameters}
    model.load_state_dict(mapping, strict=True)


def state_to_ndarrays(state: ModelState) -> tuple[NDArray[np.generic], ...]:
    _validate_state(state.parameters)
    return tuple(parameter.tensor.detach().cpu().numpy().copy() for parameter in state.parameters)


def ndarrays_to_state(
    template: ModelState,
    arrays: Sequence[NDArray[np.generic]],
) -> ModelState:
    if len(template.parameters) != len(arrays):
        raise ValueError("Aggregated parameter count does not match the model state template")
    parameters = tuple(
        TensorParameter(
            name=template_parameter.name,
            tensor=torch.from_numpy(np.asarray(array)).to(dtype=template_parameter.tensor.dtype).clone(),
        )
        for template_parameter, array in zip(template.parameters, arrays, strict=True)
    )
    _validate_state(parameters)
    for template_parameter, parameter in zip(template.parameters, parameters, strict=True):
        if template_parameter.tensor.shape != parameter.tensor.shape:
            raise ValueError("Aggregated parameter shape does not match the model state template")
    return ModelState(parameters=parameters)


def encode_global_checkpoints(checkpoints: tuple[CapturedCheckpoint, ...]) -> bytes:
    if not checkpoints:
        raise ValueError("At least one global checkpoint is required")
    tensors: dict[str, torch.Tensor] = {}
    for checkpoint in checkpoints:
        for parameter in checkpoint.state.parameters:
            key = CheckpointKey(
                round_number=checkpoint.round_number,
                state_kind=CheckpointStateKind.GLOBAL,
                parameter_name=parameter.name,
                client_id=None,
            ).render()
            if key in tensors:
                raise ValueError(f"Duplicate checkpoint tensor key '{key}'")
            tensors[key] = parameter.tensor
    return save_safetensors(tensors)


def encode_personalized_checkpoints(
    checkpoints: tuple[PersonalizedCapturedCheckpoint, ...],
) -> bytes:
    if not checkpoints:
        raise ValueError("At least one personalized checkpoint is required")
    tensors: dict[str, torch.Tensor] = {}
    for checkpoint in checkpoints:
        for client_state in checkpoint.client_states:
            for parameter in client_state.state.parameters:
                key = CheckpointKey(
                    round_number=checkpoint.round_number,
                    state_kind=CheckpointStateKind.PERSONALIZED,
                    parameter_name=parameter.name,
                    client_id=client_state.client_id,
                ).render()
                if key in tensors:
                    raise ValueError(f"Duplicate checkpoint tensor key '{key}'")
                tensors[key] = parameter.tensor
    return save_safetensors(tensors)


def decode_global_state(payload: bytes, round_number: int) -> ModelState:
    states = load_safetensors(payload)
    prefix = f"round/{round_number}/global/"
    parameters = tuple(
        TensorParameter(name=name.removeprefix(prefix), tensor=tensor.detach().cpu().clone())
        for name, tensor in sorted(states.items())
        if name.startswith(prefix)
    )
    if not parameters:
        raise ValueError(f"Global checkpoint round {round_number} is absent")
    _validate_state(parameters)
    return ModelState(parameters=parameters)


def decode_personalized_states(
    payload: bytes,
    round_number: int,
    client_ids: tuple[str, ...],
) -> tuple[ClientModelState, ...]:
    states = load_safetensors(payload)
    decoded: list[ClientModelState] = []
    for client_id in client_ids:
        prefix = f"round/{round_number}/client/{quote(client_id, safe='')}/"
        parameters = tuple(
            TensorParameter(name=name.removeprefix(prefix), tensor=tensor.detach().cpu().clone())
            for name, tensor in sorted(states.items())
            if name.startswith(prefix)
        )
        if not parameters:
            raise ValueError(f"Personalized checkpoint round {round_number} is absent for client '{client_id}'")
        _validate_state(parameters)
        decoded.append(ClientModelState(client_id=client_id, state=ModelState(parameters=parameters)))
    return tuple(decoded)


def _validate_state(parameters: tuple[TensorParameter, ...]) -> None:
    if not parameters:
        raise ValueError("Model state must contain parameters")
    names = tuple(parameter.name for parameter in parameters)
    if len(set(names)) != len(names):
        raise ValueError("Model state parameter names must be unique")
    for parameter in parameters:
        if not isinstance(parameter.tensor, torch.Tensor):
            raise TypeError("Model state values must be tensors")
        if not torch.isfinite(parameter.tensor).all():
            raise ValueError(f"Model state parameter '{parameter.name}' contains non-finite values")
