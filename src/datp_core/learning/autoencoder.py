"""Shared protocol-driven autoencoder architecture for federated training."""

from collections.abc import Sequence

import torch
from torch import nn

from datp_core.domain.enums import ContractSubject
from datp_core.domain.errors import ScientificContractError
from datp_core.domain.values import Seed
from datp_core.protocols.models import AutoencoderProtocol


class FederatedAutoencoder(nn.Module):
    """Symmetric autoencoder constructed only from the declared width tuple.

    No BatchNorm, dropout, or architecture addition is introduced. Reconstruction-error
    semantics belong to scoring, never to this class.
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


def build_federated_autoencoder(
    protocol: AutoencoderProtocol,
    *,
    initialization_seed: Seed,
) -> FederatedAutoencoder:
    """Construct a fresh autoencoder with initialization deterministic from the seed."""
    generator = torch.Generator(device="cpu")
    generator.manual_seed(initialization_seed.value)
    model = FederatedAutoencoder(protocol.widths)
    with torch.no_grad():
        for parameter in model.parameters():
            if parameter.dim() >= 2:
                nn.init.kaiming_uniform_(parameter, a=5**0.5, generator=generator)
            else:
                bound = 1.0 / max(parameter.shape[0], 1) ** 0.5
                parameter.uniform_(-bound, bound, generator=generator)
    model.train()
    return model


def clone_autoencoder_state(model: FederatedAutoencoder) -> dict[str, torch.Tensor]:
    return {name: tensor.detach().clone() for name, tensor in model.state_dict().items()}


def load_autoencoder_state(model: FederatedAutoencoder, state: dict[str, torch.Tensor]) -> None:
    model.load_state_dict(state, strict=True)
