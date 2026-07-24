"""CUDA device selection for required-CUDA training."""

from __future__ import annotations

import torch


def require_cuda_training_device() -> str:
    """Return CUDA only when available; scientific training may never silently fall back."""
    if not torch.cuda.is_available():
        raise ValueError("Configured CUDA-required training cannot run because no CUDA device is available")
    return "cuda"
