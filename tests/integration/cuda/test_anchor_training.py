import pytest
import torch

from datp_core.domain.learning.training import DeterminismLevel
from datp_core.domain.runtime.seeds import Seed
from datp_core.infrastructure.learning.models.anchor_training import (
    ANCHOR_AUTOENCODER_SPECIFICATION,
    anchor_training_spec,
    build_anchor_optimizer,
)
from datp_core.infrastructure.learning.models.autoencoder import build_fixed_autoencoder
from datp_core.infrastructure.runtime.determinism import configure_determinism
from tests.support.cuda_lane import skip_if_cuda_unavailable


def _run_one_smoke_step(*, initialization_seed: Seed, batch: torch.Tensor) -> torch.Tensor:
    model = build_fixed_autoencoder(
        specification=ANCHOR_AUTOENCODER_SPECIFICATION, initialization_seed=initialization_seed
    ).to("cuda")
    training = anchor_training_spec(seed=initialization_seed)
    optimizer = build_anchor_optimizer(model=model, training=training)

    optimizer.zero_grad()
    reconstruction = model(batch)
    loss = ((reconstruction - batch) ** 2).mean(dim=1).mean()
    loss.backward()
    optimizer.step()

    with torch.no_grad():
        return model(batch)


@pytest.mark.cuda
def test_anchor_autoencoder_forward_backward_optimizer_step_is_bit_identical_on_cuda() -> None:
    skip_if_cuda_unavailable()
    configure_determinism(DeterminismLevel.STRICT)
    batch = torch.ones(4, ANCHOR_AUTOENCODER_SPECIFICATION.input_dim, device="cuda")

    first = _run_one_smoke_step(initialization_seed=Seed(value=23), batch=batch)
    second = _run_one_smoke_step(initialization_seed=Seed(value=23), batch=batch)

    assert torch.equal(first, second)
