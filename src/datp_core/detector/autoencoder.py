from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

import numpy as np
import torch
from torch import nn

from datp_core.core.errors import (
    ErrorMessage,
    ScientificContractError,
)
from datp_core.core.identifiers import ContractSubject, OptimizerId
from datp_core.core.numeric import BatchSize, FeatureCount, LearningRate, RowCount, Seed
from datp_core.detector.training.contracts import AutoencoderArchitecture, AutoencoderProtocol, OptimizerProtocol
from datp_core.runtime.compute import require_cuda_available

LEARNING_DTYPE = np.float32
TORCH_LEARNING_DTYPE = torch.float32


class AutoencoderStateContribution(Protocol):
    @property
    def model_state(self) -> "AutoencoderModelState": ...

    @property
    def sample_count(self) -> RowCount: ...


@dataclass(frozen=True, slots=True, eq=False, init=False)
class AutoencoderModelState:
    _parameters: Mapping[str, torch.Tensor] = field(repr=False)

    @classmethod
    def _from_tensor_mapping(cls, tensors: Mapping[str, object]) -> "AutoencoderModelState":
        if not tensors:
            raise ScientificContractError(
                ErrorMessage("an autoencoder model state requires at least one parameter"),
                subject=ContractSubject.TRAINING,
            )
        if any(not name for name in tensors):
            raise ScientificContractError(
                ErrorMessage("autoencoder model-state parameter names cannot be empty"),
                subject=ContractSubject.TRAINING,
            )
        validated_tensors: dict[str, torch.Tensor] = {}
        for name, tensor in tensors.items():
            if not isinstance(tensor, torch.Tensor):
                raise ScientificContractError(
                    ErrorMessage("autoencoder model states can contain only torch tensors"),
                    subject=ContractSubject.TRAINING,
                )
            validated_tensors[name] = tensor
        instance = cls.__new__(cls)
        object.__setattr__(
            instance,
            "_parameters",
            MappingProxyType({name: tensor.detach().clone() for name, tensor in validated_tensors.items()}),
        )
        return instance

    @classmethod
    def from_model(cls, model: "ReconstructionAutoencoder") -> "AutoencoderModelState":
        return cls.from_torch_state_dict(model.state_dict())

    @classmethod
    def from_torch_state_dict(cls, state_dict: Mapping[str, torch.Tensor]) -> "AutoencoderModelState":
        return cls._from_tensor_mapping(state_dict)

    def to_torch_state_dict(self) -> dict[str, torch.Tensor]:
        return {name: tensor.detach().clone() for name, tensor in self._parameters.items()}

    def on_cpu_with_contiguous_tensors(self) -> "AutoencoderModelState":
        return AutoencoderModelState._from_tensor_mapping(
            {name: tensor.detach().cpu().contiguous() for name, tensor in self._parameters.items()}
        )

    def apply_to(self, model: "ReconstructionAutoencoder") -> None:
        model.load_state_dict(self.to_torch_state_dict(), strict=True)

    def is_equivalent_to(self, other: "AutoencoderModelState") -> bool:
        if self._parameters.keys() != other._parameters.keys():
            return False
        return all(torch.equal(tensor, other._parameters[name]) for name, tensor in self._parameters.items())

    @property
    def trainable_parameter_count(self) -> int:
        """Number of scalar parameters represented by this state."""

        return sum(tensor.numel() for tensor in self._parameters.values())

    def l2_distance_to(self, other: "AutoencoderModelState") -> float:
        """Compute an exact float64 L2 distance between like-for-like model states."""

        if self._parameters.keys() != other._parameters.keys():
            raise ScientificContractError(
                ErrorMessage("model-state drift requires identical parameter keys"),
                subject=ContractSubject.TRAINING,
            )
        squared_distance = 0.0
        for name, tensor in self._parameters.items():
            reference = other._parameters[name]
            if tensor.shape != reference.shape:
                raise ScientificContractError(
                    ErrorMessage("model-state drift requires identical parameter shapes"),
                    subject=ContractSubject.TRAINING,
                )
            difference = tensor.detach().to(dtype=torch.float64, device="cpu") - reference.detach().to(
                dtype=torch.float64, device="cpu"
            )
            squared_distance += float(torch.sum(torch.square(difference)).item())
        return float(np.sqrt(squared_distance))

    @classmethod
    def sample_weighted_average(
        cls,
        contributions: Sequence[AutoencoderStateContribution],
    ) -> "AutoencoderModelState":
        if not contributions:
            raise ScientificContractError(
                ErrorMessage("aggregation requires at least one client update"),
                subject=ContractSubject.CLIENT,
            )
        total_samples = sum(contribution.sample_count.value for contribution in contributions)
        if total_samples < 1:
            raise ScientificContractError(
                ErrorMessage("aggregation requires a positive total sample count"),
                subject=ContractSubject.ROWS,
            )

        reference = contributions[0].model_state
        parameter_names = tuple(reference._parameters)
        for contribution in contributions[1:]:
            candidate = contribution.model_state
            if tuple(candidate._parameters) != parameter_names:
                raise ScientificContractError(
                    ErrorMessage("client update parameter keys do not match"),
                    subject=ContractSubject.TRAINING,
                )
            for name in parameter_names:
                expected = reference._parameters[name]
                observed = candidate._parameters[name]
                if (
                    expected.shape != observed.shape
                    or expected.dtype != observed.dtype
                    or expected.device != observed.device
                ):
                    raise ScientificContractError(
                        ErrorMessage("client update parameter shapes, dtypes, or devices do not match"),
                        subject=ContractSubject.TRAINING,
                    )

        aggregate: dict[str, torch.Tensor] = {}
        for name in parameter_names:
            weighted_sum = torch.zeros_like(reference._parameters[name], dtype=torch.float64)
            for contribution in contributions:
                weight = contribution.sample_count.value / total_samples
                weighted_sum.add_(
                    contribution.model_state._parameters[name].to(torch.float64),
                    alpha=weight,
                )
            aggregate[name] = weighted_sum.to(reference._parameters[name].dtype)
        return cls._from_tensor_mapping(aggregate)


class ReconstructionAutoencoder(nn.Module):
    def __init__(self, widths: AutoencoderArchitecture) -> None:
        super().__init__()
        final_layer_index = len(widths) - 2
        layers: list[nn.Module] = []
        for layer_index, (left, right) in enumerate(zip(widths[:-1], widths[1:], strict=True)):
            layers.append(nn.Linear(left.value, right.value))
            if layer_index != final_layer_index:
                layers.append(nn.ReLU())
        self._network = nn.Sequential(*layers)
        self._widths = widths

    @property
    def input_width(self) -> FeatureCount:
        return self._widths.input_width

    @property
    def widths(self) -> AutoencoderArchitecture:
        return self._widths

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self._network(features)


def construct_autoencoder(protocol: AutoencoderProtocol) -> ReconstructionAutoencoder:
    return ReconstructionAutoencoder(protocol.widths)


def build_optimizer(
    model: ReconstructionAutoencoder,
    optimizer_protocol: OptimizerProtocol,
    learning_rate: LearningRate,
) -> torch.optim.Optimizer:
    match optimizer_protocol.identity:
        case OptimizerId.ADAM:
            return torch.optim.Adam(
                model.parameters(),
                lr=learning_rate.value,
                weight_decay=optimizer_protocol.weight_decay.value,
            )
        case _:
            raise ScientificContractError(
                ErrorMessage(f"unsupported optimizer {optimizer_protocol.identity}"),
                subject=ContractSubject.OPTIMIZER,
            )


def build_reconstruction_autoencoder(
    protocol: AutoencoderProtocol,
    *,
    initialization_seed: Seed,
) -> ReconstructionAutoencoder:
    model = construct_autoencoder(protocol)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(initialization_seed.value)
    with torch.no_grad():
        for module in model.modules():
            if not isinstance(module, nn.Linear):
                continue
            nn.init.kaiming_uniform_(module.weight, a=5**0.5, generator=generator)
            fan_in = module.weight.shape[1]
            bound = 1.0 / fan_in**0.5
            nn.init.uniform_(module.bias, -bound, bound, generator=generator)
    model.train()
    return model


def build_autoencoder_for_state(
    protocol: AutoencoderProtocol,
    model_state: AutoencoderModelState,
    *,
    device: torch.device,
) -> ReconstructionAutoencoder:
    model = construct_autoencoder(protocol).to(device)
    model_state.apply_to(model)
    return model


def _require_scoreable_feature_matrix(model: ReconstructionAutoencoder, features: np.ndarray) -> None:
    if features.ndim != 2:
        raise ScientificContractError(
            ErrorMessage("reconstruction scoring requires a two-dimensional feature matrix"),
            subject=ContractSubject.FEATURES,
        )
    if features.shape[1] != model.input_width.value:
        raise ScientificContractError(
            ErrorMessage("feature width mismatch during scoring"),
            subject=ContractSubject.FEATURES,
        )
    if not np.isfinite(features).all():
        raise ScientificContractError(ErrorMessage("scoring features must be finite"), subject=ContractSubject.FEATURES)


def _require_model_on_device(model: ReconstructionAutoencoder, device: torch.device) -> None:
    parameters = tuple(model.parameters())
    if not parameters:
        raise ScientificContractError(
            ErrorMessage("reconstruction autoencoder has no parameters"),
            subject=ContractSubject.TRAINING,
        )
    if any(parameter.device != device for parameter in parameters):
        raise ScientificContractError(
            ErrorMessage("autoencoder parameters must all reside on the declared scoring device"),
            subject=ContractSubject.CUDA,
        )
    if any(parameter.dtype != TORCH_LEARNING_DTYPE for parameter in parameters):
        raise ScientificContractError(
            ErrorMessage("autoencoder parameters must use the canonical learning dtype"),
            subject=ContractSubject.TRAINING,
        )


def reconstruction_errors(
    model: ReconstructionAutoencoder,
    features: np.ndarray,
    *,
    batch_size: BatchSize,
    device: torch.device,
) -> np.ndarray:
    require_cuda_available()
    if device.type != "cuda":
        raise ScientificContractError(
            ErrorMessage("reconstruction scoring requires a CUDA device"), subject=ContractSubject.CUDA
        )
    _require_scoreable_feature_matrix(model, features)
    _require_model_on_device(model, device)

    model.eval()
    scores: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, features.shape[0], batch_size.value):
            batch_array = np.asarray(features[start : start + batch_size.value], dtype=LEARNING_DTYPE)
            batch = torch.as_tensor(batch_array, dtype=TORCH_LEARNING_DTYPE, device=device)
            reconstruction = model(batch)
            per_row = torch.mean((reconstruction - batch) ** 2, dim=1)
            scores.append(per_row.detach().cpu().numpy())

    if not scores:
        return np.empty(0, dtype=np.float64)
    return np.concatenate(scores).astype(np.float64, copy=False)
