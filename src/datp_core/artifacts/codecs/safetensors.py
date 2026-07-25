"""The one sanctioned SafeTensors call site for model-tensor persistence.

Every SafeTensors read/write in the codebase goes through the direct-file store APIs here.
"""

from __future__ import annotations

import torch
from safetensors.torch import load as load_safetensors_bytes
from safetensors.torch import save as save_safetensors_bytes

from datp_core.artifacts.store import ArtifactStore
from datp_core.core.hashing import Checksum


def save_model_safetensors_to_store(
    model_state_dict: dict[str, torch.Tensor],
    *,
    store: ArtifactStore,
    relative_path: str,
    replace: bool = False,
) -> Checksum:
    """Atomically persist model tensors through the direct-file store."""
    clean_tensors = {key: tensor.cpu().contiguous() for key, tensor in model_state_dict.items()}
    return store.write_bytes_atomic(relative_path, save_safetensors_bytes(clean_tensors), replace=replace)


def load_model_safetensors_from_store(
    relative_path: str,
    *,
    store: ArtifactStore,
    expected_checksum: Checksum | None = None,
) -> dict[str, torch.Tensor]:
    """Load direct-file tensors after optional checksum validation."""
    if expected_checksum is not None:
        store.validate_file(relative_path, expected_checksum)
    return load_safetensors_bytes(store.read_bytes(relative_path))


__all__ = [
    "load_model_safetensors_from_store",
    "save_model_safetensors_to_store",
]
