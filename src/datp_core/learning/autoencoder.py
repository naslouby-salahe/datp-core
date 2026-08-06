"""Protocol-driven reconstruction autoencoder construction and scoring."""

from collections.abc import Mapping, Sequence

import numpy as np
import torch
from torch import nn

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values.counts import BatchSize, Seed
from datp_core.protocols.training import AutoencoderArchitecture, AutoencoderProtocol
from datp_core.runtime.compute import require_cuda_available

type AutoencoderState = dict[str, torch.Tensor]
type AutoencoderStateView = Mapping[str, torch.Tensor]

LEARNING_DTYPE = np.float32
TORCH_LEARNING_DTYPE = torch.float32


class ReconstructionAutoencoder(nn.Module):
    """Symmetric feed-forward autoencoder defined by the declared widths."""

    def __init__(self, widths: Sequence[int]) -> None:
        super().__init__()
        declared = _validated_widths(widths)
        final_layer_index = len(declared) - 2
        layers: list[nn.Module] = []
        for layer_index, (left, right) in enumerate(zip(declared[:-1], declared[1:], strict=True)):
            layers.append(nn.Linear(left, right))
            if layer_index != final_layer_index:
                layers.append(nn.ReLU())
        self._network = nn.Sequential(*layers)
        self._widths = declared

    @property
    def input_width(self) -> int:
        return self._widths[0]

    @property
    def widths(self) -> tuple[int, ...]:
        return self._widths

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self._network(features)


def _validated_widths(widths: Sequence[int]) -> tuple[int, ...]:
    try:
        return tuple(AutoencoderArchitecture(tuple(widths)))
    except ValueError as error:
        raise ScientificContractError(str(error), subject=ContractSubject.WIDTHS) from error


def _construct_autoencoder(protocol: AutoencoderProtocol) -> ReconstructionAutoencoder:
    """Construct without advancing the caller's global CPU RNG state."""
    with torch.random.fork_rng(devices=[]):
        return ReconstructionAutoencoder(protocol.widths)


def build_reconstruction_autoencoder(
    protocol: AutoencoderProtocol,
    *,
    initialization_seed: Seed,
) -> ReconstructionAutoencoder:
    """Construct and initialize a fresh deterministic autoencoder."""
    model = _construct_autoencoder(protocol)
    generator = torch.Generator(device="cpu")
    generator.manual_seed(initialization_seed.value)
    with torch.no_grad():
        for module in model.modules():
            if not isinstance(module, nn.Linear):
                continue
            nn.init.kaiming_uniform_(module.weight, a=5**0.5, generator=generator)
            if module.bias is None:
                continue
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(module.weight)
            bound = 1.0 / fan_in**0.5
            nn.init.uniform_(module.bias, -bound, bound, generator=generator)
    model.train()
    return model


def build_autoencoder_for_state(
    protocol: AutoencoderProtocol,
    state: AutoencoderStateView,
    *,
    device: torch.device,
) -> ReconstructionAutoencoder:
    """Construct an isolated model, load a complete state, and place it on the target device."""
    model = _construct_autoencoder(protocol).to(device)
    load_autoencoder_state(model, state)
    return model


def clone_state(state: AutoencoderStateView) -> AutoencoderState:
    return {name: tensor.detach().clone() for name, tensor in state.items()}


def clone_autoencoder_state(model: ReconstructionAutoencoder) -> AutoencoderState:
    return clone_state(model.state_dict())


def load_autoencoder_state(model: ReconstructionAutoencoder, state: AutoencoderStateView) -> None:
    model.load_state_dict(state, strict=True)


def _require_scoreable_feature_matrix(model: ReconstructionAutoencoder, features: np.ndarray) -> None:
    if features.ndim != 2:
        raise ScientificContractError(
            "reconstruction scoring requires a two-dimensional feature matrix",
            subject=ContractSubject.FEATURES,
        )
    if features.shape[1] != model.input_width:
        raise ScientificContractError(
            "feature width mismatch during scoring",
            subject=ContractSubject.FEATURES,
        )
    if not np.isfinite(features).all():
        raise ScientificContractError(
            "scoring features must be finite",
            subject=ContractSubject.FEATURES,
        )


def _require_model_on_device(model: ReconstructionAutoencoder, device: torch.device) -> None:
    parameters = tuple(model.parameters())
    if not parameters:
        raise ScientificContractError(
            "reconstruction autoencoder has no parameters",
            subject=ContractSubject.TRAINING,
        )
    if any(parameter.device != device for parameter in parameters):
        raise ScientificContractError(
            "autoencoder parameters must all reside on the declared scoring device",
            subject=ContractSubject.CUDA,
        )
    if any(parameter.dtype != TORCH_LEARNING_DTYPE for parameter in parameters):
        raise ScientificContractError(
            "autoencoder parameters must use the canonical learning dtype",
            subject=ContractSubject.TRAINING,
        )


def reconstruction_errors(
    model: ReconstructionAutoencoder,
    features: np.ndarray,
    *,
    batch_size: BatchSize,
    device: torch.device,
) -> np.ndarray:
    """Return mean per-row squared reconstruction error."""
    require_cuda_available()
    if device.type != "cuda":
        raise ScientificContractError(
            "reconstruction scoring requires a CUDA device",
            subject=ContractSubject.CUDA,
        )
    _require_scoreable_feature_matrix(model, features)
    _require_model_on_device(model, device)

    model.eval()
    scores: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, features.shape[0], batch_size.value):
            batch_array = np.asarray(
                features[start : start + batch_size.value],
                dtype=LEARNING_DTYPE,
            )
            batch = torch.as_tensor(
                batch_array,
                dtype=TORCH_LEARNING_DTYPE,
                device=device,
            )
            reconstruction = model(batch)
            per_row = torch.mean((reconstruction - batch) ** 2, dim=1)
            scores.append(per_row.detach().cpu().numpy())

    if not scores:
        return np.empty(0, dtype=np.float64)
    return np.concatenate(scores).astype(np.float64, copy=False)
