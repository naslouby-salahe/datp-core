import pytest
import torch
from torch import Tensor, nn

from datp_core.infrastructure.scoring.calibration import BatchedCudaReconstructionScorer, TensorScoreCollector
from tests.support.cuda_lane import skip_if_cuda_unavailable


class _DoubleModel(nn.Module):
    def forward(self, values: Tensor) -> Tensor:
        return values * 2


@pytest.mark.cuda
def test_batched_cuda_scoring_matches_a_single_pass_synthetic_reference() -> None:
    skip_if_cuda_unavailable()
    values = torch.arange(24, dtype=torch.float32).reshape(6, 4)
    collector = TensorScoreCollector(batches=[])
    scorer = BatchedCudaReconstructionScorer(model=_DoubleModel().cuda(), device=torch.device("cuda"))

    count = scorer.score(batches=(values[:2], values[2:5], values[5:]), sink=collector)
    reference = torch.mean(torch.square(values), dim=1)

    assert count == len(values)
    assert torch.equal(collector.values(), reference)
