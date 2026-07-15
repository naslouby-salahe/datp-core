import pytest
import torch

from datp_core.domain.learning.models import ActivationFunction, AutoencoderSpec
from datp_core.domain.learning.training import DeterminismLevel
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.learning.models.autoencoder import build_fixed_autoencoder
from datp_core.infrastructure.runtime.determinism import configure_determinism
from tests.support.cuda_lane import skip_if_cuda_unavailable


@pytest.mark.cuda
def test_strict_cuda_runs_are_bit_identical_on_synthetic_inputs() -> None:
    skip_if_cuda_unavailable()
    configure_determinism(DeterminismLevel.STRICT)
    specification = AutoencoderSpec(
        input_dim=4,
        hidden_dims=(80, 40),
        bottleneck_dim=20,
        activation=ActivationFunction.RELU,
    )
    first = build_fixed_autoencoder(specification=specification, initialization_seed=Seed(value=19)).to("cuda")
    second = build_fixed_autoencoder(specification=specification, initialization_seed=Seed(value=19)).to("cuda")
    values = torch.ones(2, 4, device="cuda")

    assert torch.equal(first(values), second(values))
