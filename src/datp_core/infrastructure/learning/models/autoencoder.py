from math import sqrt
from typing import assert_never

import torch
from torch import Tensor, nn

from datp_core.domain.errors import DomainValidationError
from datp_core.domain.learning.models import (
    ActivationFunction,
    AutoencoderSpec,
)
from datp_core.domain.runtime.seeds import Seed


class FixedAutoencoder(nn.Module):
    def __init__(self, specification: AutoencoderSpec) -> None:
        super().__init__()
        _validate_fixed_architecture(specification)
        encoder_dimensions = (
            specification.input_dim,
            *specification.hidden_dims,
            specification.bottleneck_dim,
        )
        decoder_dimensions = (
            specification.bottleneck_dim,
            *reversed(specification.hidden_dims),
            specification.input_dim,
        )
        self.encoder = _network(encoder_dimensions, specification.activation, final_activation=True)
        self.decoder = _network(decoder_dimensions, specification.activation, final_activation=False)

    def encode(self, values: Tensor) -> Tensor:
        return self.encoder(values)

    def decode(self, values: Tensor) -> Tensor:
        return self.decoder(values)

    def forward(self, values: Tensor) -> Tensor:
        return self.decode(self.encode(values))


def build_fixed_autoencoder(*, specification: AutoencoderSpec, initialization_seed: Seed) -> FixedAutoencoder:
    model = FixedAutoencoder(specification)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(initialization_seed.value)
    with torch.no_grad():
        for module in model.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(module.weight, a=sqrt(5), generator=generator)
                bound = 1 / sqrt(module.in_features)
                nn.init.uniform_(module.bias, -bound, bound, generator=generator)
    return model


def _network(dimensions: tuple[int, ...], activation: ActivationFunction, *, final_activation: bool) -> nn.Sequential:
    layers: list[nn.Module] = []
    for index, (input_features, output_features) in enumerate(zip(dimensions[:-1], dimensions[1:], strict=True)):
        layers.append(nn.Linear(input_features, output_features))
        if final_activation or index < len(dimensions) - 2:
            layers.append(_activation(activation))
    return nn.Sequential(*layers)


def _activation(activation: ActivationFunction) -> nn.Module:
    match activation:
        case ActivationFunction.RELU:
            return nn.ReLU()
        case ActivationFunction.LEAKY_RELU:
            return nn.LeakyReLU()
        case ActivationFunction.TANH:
            return nn.Tanh()
        case ActivationFunction.SIGMOID:
            return nn.Sigmoid()
        case ActivationFunction.ELU:
            return nn.ELU()
        case _ as unreachable:
            assert_never(unreachable)


def _validate_fixed_architecture(specification: AutoencoderSpec) -> None:
    actual_architecture = (
        specification.hidden_dims,
        specification.bottleneck_dim,
        specification.activation,
    )
    if actual_architecture == ((80, 40), 20, ActivationFunction.RELU):
        return
    raise DomainValidationError(
        detail="the fixed autoencoder requires ReLU encoder widths 80, 40, and 20",
        value=repr(specification),
        constraint="hidden_dims == (80, 40); bottleneck_dim == 20; activation == RELU",
    )
