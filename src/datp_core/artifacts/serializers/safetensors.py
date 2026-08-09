"""SafeTensors state-dict serialization shared by checkpoint, scoring, and communication-cost code."""

from collections.abc import Mapping
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file

from datp_core.artifacts.provenance import Checksum, checksum_file


def to_cpu_contiguous_state(state_dict: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    """Detach and move a state dict to a CPU-contiguous form suitable for SafeTensors serialization."""
    return {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}


def save_state_dict_tensors(state_dict: Mapping[str, torch.Tensor], path: Path) -> Checksum:
    """Persist a state dict as a SafeTensors file and return its checksum."""
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file(to_cpu_contiguous_state(state_dict), str(path))
    return checksum_file(path)


def load_state_dict_tensors(path: Path, device: torch.device | str) -> dict[str, torch.Tensor]:
    """Load a SafeTensors state dict onto the given device."""
    return load_file(str(path), device=str(device))
