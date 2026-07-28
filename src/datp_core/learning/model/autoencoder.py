"""Configuration-driven dense autoencoder construction."""

from __future__ import annotations

import torch
from torch import nn

from datp_core.learning.contracts.enums import (
    ActivationKind,
    BiasInitializationKind,
    NormalizationKind,
    OutputActivationKind,
    WeightInitializationKind,
)
from datp_core.learning.contracts.model import DenseAutoencoderProfile
from datp_core.learning.model.runtime import TorchRuntime, seed_everything


class DenseAutoencoder(nn.Module):
    def __init__(
        self,
        encoder: nn.Sequential,
        decoder: nn.Sequential,
    ) -> None:
        super().__init__()
        self.encoder = encoder
        self.decoder = decoder

    def forward(self, inputs: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(inputs))


def build_autoencoder(
    profile: DenseAutoencoderProfile,
    input_dimension: int,
    initialization_seed: int,
    runtime: TorchRuntime,
) -> DenseAutoencoder:
    if input_dimension < 1:
        raise ValueError("Autoencoder input dimension must be positive")
    seed_everything(initialization_seed)
    hidden_dimensions = tuple(int(value) for value in profile.hidden_dimensions)
    encoder = _build_encoder(profile, input_dimension, hidden_dimensions)
    decoder = _build_decoder(profile, input_dimension, hidden_dimensions)
    model = DenseAutoencoder(encoder=encoder, decoder=decoder)
    _initialize_parameters(model, profile)
    return model.to(device=runtime.device, dtype=runtime.dtype)


def _build_encoder(
    profile: DenseAutoencoderProfile,
    input_dimension: int,
    hidden_dimensions: tuple[int, ...],
) -> nn.Sequential:
    layers: list[nn.Module] = []
    current_dimension = input_dimension
    for output_dimension in hidden_dimensions:
        layers.append(nn.Linear(current_dimension, output_dimension, bias=profile.use_bias))
        _append_normalization(layers, profile.normalization, output_dimension)
        layers.append(_activation(profile.activation))
        current_dimension = output_dimension
    return nn.Sequential(*layers)


def _build_decoder(
    profile: DenseAutoencoderProfile,
    input_dimension: int,
    hidden_dimensions: tuple[int, ...],
) -> nn.Sequential:
    output_dimensions = tuple(reversed(hidden_dimensions[:-1])) + (input_dimension,)
    layers: list[nn.Module] = []
    current_dimension = hidden_dimensions[-1]
    for index, output_dimension in enumerate(output_dimensions):
        final_layer = index == len(output_dimensions) - 1
        layers.append(nn.Linear(current_dimension, output_dimension, bias=profile.use_bias))
        if final_layer:
            layers.append(_output_activation(profile.output_activation))
        else:
            _append_normalization(layers, profile.normalization, output_dimension)
            layers.append(_activation(profile.activation))
        current_dimension = output_dimension
    return nn.Sequential(*layers)


def _append_normalization(
    layers: list[nn.Module],
    normalization: NormalizationKind,
    dimension: int,
) -> None:
    match normalization:
        case NormalizationKind.NONE:
            return
        case NormalizationKind.BATCH_NORMALIZATION:
            layers.append(nn.BatchNorm1d(dimension))
        case NormalizationKind.LAYER_NORMALIZATION:
            layers.append(nn.LayerNorm(dimension))
        case _:
            raise ValueError(f"Unsupported normalization '{normalization.value}'")


def _activation(kind: ActivationKind) -> nn.Module:
    match kind:
        case ActivationKind.RELU:
            return nn.ReLU()
        case ActivationKind.LEAKY_RELU:
            return nn.LeakyReLU()
        case ActivationKind.GELU:
            return nn.GELU()
        case ActivationKind.ELU:
            return nn.ELU()
    raise ValueError(f"Unsupported activation '{kind.value}'")


def _output_activation(kind: OutputActivationKind) -> nn.Module:
    match kind:
        case OutputActivationKind.IDENTITY:
            return nn.Identity()
        case OutputActivationKind.SIGMOID:
            return nn.Sigmoid()
        case OutputActivationKind.TANH:
            return nn.Tanh()
    raise ValueError(f"Unsupported output activation '{kind.value}'")


def _initialize_parameters(model: nn.Module, profile: DenseAutoencoderProfile) -> None:
    for module in model.modules():
        if not isinstance(module, nn.Linear):
            continue
        match profile.weight_initialization:
            case WeightInitializationKind.KAIMING_UNIFORM:
                nn.init.kaiming_uniform_(module.weight, nonlinearity="relu")
            case WeightInitializationKind.XAVIER_UNIFORM:
                nn.init.xavier_uniform_(module.weight)
            case _:
                raise ValueError(
                    f"Unsupported weight initialization '{profile.weight_initialization.value}'"
                )
        if module.bias is None:
            continue
        match profile.bias_initialization:
            case BiasInitializationKind.ZERO:
                nn.init.zeros_(module.bias)
            case _:
                raise ValueError(
                    f"Unsupported bias initialization '{profile.bias_initialization.value}'"
                )
