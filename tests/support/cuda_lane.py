import pytest
import torch


def skip_if_cuda_unavailable() -> None:
    """Apply the CUDA `TestDeviceRequirement` skip policy: skip cleanly, never fail."""
    if not torch.cuda.is_available():
        pytest.skip("no CUDA device available on this runner; skip is the correct policy outcome")
