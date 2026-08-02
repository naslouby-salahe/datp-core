"""Shared protocol-driven reconstruction autoencoder architecture."""

from collections.abc import Sequence

import numpy as np
import torch
from torch import nn

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import BatchSize, Seed
from datp_core.protocols.models import AutoencoderProtocol
from datp_core.runtime.compute import require_cuda_available

type AutoencoderState = dict[str, torch.Tensor]
LEARNING_DTYPE = np.float32
TORCH_LEARNING_DTYPE = torch.float32


class ReconstructionAutoencoder(nn.Module):
    """Symmetric autoencoder constructed only from the declared width tuple.

    No BatchNorm, dropout, or architecture addition is introduced. Per-row reconstruction-error
    aggregation is provided by reconstruction_errors; trainers must not invent alternate score semantics.
    """

    def __init__(self, widths: Sequence[int]) -> None:
        super().__init__()
        if len(widths) < 2:
            raise ScientificContractError(
                "autoencoder widths require at least input and output layers",
                subject=ContractSubject.WIDTHS,
            )
        if widths[0] != widths[-1]:
            raise ScientificContractError(
                "autoencoder input and output widths must match",
                subject=ContractSubject.WIDTHS,
            )
        layers: list[nn.Module] = []
        for left, right in zip(widths[:-1], widths[1:], strict=True):
            layers.append(nn.Linear(left, right))
            if right != widths[-1]:
                layers.append(nn.ReLU())
        self._network = nn.Sequential(*layers)
        self._input_width = int(widths[0])
        self._widths = tuple(int(width) for width in widths)

    @property
    def input_width(self) -> int:
        return self._input_width

    @property
    def widths(self) -> tuple[int, ...]:
        return self._widths

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self._network(features)


def build_reconstruction_autoencoder(
    protocol: AutoencoderProtocol,
    *,
    initialization_seed: Seed,
) -> ReconstructionAutoencoder:
    """Construct a fresh autoencoder with initialization deterministic from the seed."""
    generator = torch.Generator(device="cpu")
    generator.manual_seed(initialization_seed.value)
    model = ReconstructionAutoencoder(protocol.widths)
    with torch.no_grad():
        for module in model.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_uniform_(module.weight, a=5**0.5, generator=generator)
                if module.bias is not None:
                    fan_in, _ = nn.init._calculate_fan_in_and_fan_out(module.weight)
                    bound = 1.0 / (fan_in**0.5) if fan_in > 0 else 0.0
                    nn.init.uniform_(module.bias, -bound, bound, generator=generator)
    model.train()
    return model


def clone_state(state: AutoencoderState) -> AutoencoderState:
    return {name: tensor.detach().clone() for name, tensor in state.items()}


def clone_autoencoder_state(model: ReconstructionAutoencoder) -> AutoencoderState:
    return clone_state(dict(model.state_dict()))


def load_autoencoder_state(model: ReconstructionAutoencoder, state: AutoencoderState) -> None:
    model.load_state_dict(state, strict=True)


def _require_scoreable_feature_matrix(model: ReconstructionAutoencoder, features: np.ndarray) -> None:
    if features.ndim != 2:
        raise ScientificContractError(
            "reconstruction scoring requires a 2-D feature matrix",
            subject=ContractSubject.FEATURES,
        )
    if features.shape[1] != model.input_width:
        raise ScientificContractError("feature width mismatch during scoring", subject=ContractSubject.FEATURES)
    if not np.isfinite(features).all():
        raise ScientificContractError("scoring features must be finite", subject=ContractSubject.FEATURES)


def reconstruction_errors(
    model: ReconstructionAutoencoder,
    features: np.ndarray,
    *,
    batch_size: BatchSize,
    device: torch.device,
) -> np.ndarray:
    """Mean per-row squared reconstruction error; higher means greater anomaly evidence."""
    require_cuda_available()
    _require_scoreable_feature_matrix(model, features)
    model.eval()
    scores: list[np.ndarray] = []
    total_rows = features.shape[0]
    with torch.inference_mode():
        for start in range(0, total_rows, batch_size.value):
            batch_np = np.asarray(features[start : start + batch_size.value], dtype=LEARNING_DTYPE)
            batch_tensor = torch.as_tensor(batch_np, device=device)
            reconstructed = model(batch_tensor)
            per_row = torch.mean((reconstructed - batch_tensor) ** 2, dim=1)
            scores.append(per_row.detach().cpu().numpy())
    if not scores:
        return np.asarray([], dtype=np.float64)
    return np.concatenate(scores).astype(np.float64, copy=False)
