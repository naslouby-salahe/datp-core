"""Deterministic seeding utilities for reproducible model training."""

from __future__ import annotations

import random

import numpy as np
import torch

from datp_core.core.hashing import derive_seed


def set_deterministic_seeds(seed: int) -> None:
    """Set deterministic random seeds across Python, NumPy, PyTorch CPU and CUDA."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def derive_model_initialization_seed(*, key: str, digest_bytes: int, training_seed: int) -> int:
    """Derive the configured model-initialization seed from its declared namespace."""
    return derive_seed(key, digest_bytes, (("training_seed", training_seed),))


def derive_dataloader_shuffle_seed(
    *,
    key: str,
    digest_bytes: int,
    training_seed: int,
    round_number: int,
    client_id: str,
    local_epoch: int,
) -> int:
    """Derive the configured per-client, per-round, per-local-epoch dataloader shuffle seed."""
    return derive_seed(
        key,
        digest_bytes,
        (
            ("client_identifier", client_id),
            ("local_epoch_index", local_epoch),
            ("round_index", round_number),
            ("training_seed", training_seed),
        ),
    )
