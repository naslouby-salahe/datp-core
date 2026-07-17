from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.errors import DomainValidationError


class ActivationFunction(StrEnum):
    RELU = "relu"
    LEAKY_RELU = "leaky_relu"
    TANH = "tanh"
    SIGMOID = "sigmoid"
    ELU = "elu"


@dataclass(frozen=True, slots=True, kw_only=True)
class AutoencoderSpec:
    input_dim: int
    hidden_dims: tuple[int, ...]
    bottleneck_dim: int
    activation: ActivationFunction

    def __post_init__(self) -> None:
        if not _is_valid_autoencoder_specification(self):
            raise DomainValidationError(
                detail="autoencoder requires positive dimensions and a supported activation",
                value=repr(self),
                constraint="positive dimensions and ActivationFunction",
            )


def _is_valid_autoencoder_specification(specification: AutoencoderSpec) -> bool:
    return all(
        (
            _is_positive_dimension(specification.input_dim),
            _are_positive_hidden_dimensions(specification.hidden_dims),
            _is_positive_dimension(specification.bottleneck_dim),
            type(specification.activation) is ActivationFunction,
        )
    )


def _is_positive_dimension(value: int) -> bool:
    return type(value) is int and value >= 1


def _are_positive_hidden_dimensions(values: tuple[int, ...]) -> bool:
    return type(values) is tuple and bool(values) and all(_is_positive_dimension(value) for value in values)
