from collections.abc import Mapping
from pathlib import Path

import torch
from safetensors.torch import load_file, save_file


def to_cpu_contiguous_state(state_dict: Mapping[str, torch.Tensor]) -> dict[str, torch.Tensor]:
    return {name: tensor.detach().cpu().contiguous() for name, tensor in state_dict.items()}


def save_state_dict_tensors(state_dict: Mapping[str, torch.Tensor], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    save_file(to_cpu_contiguous_state(state_dict), str(path))


def load_state_dict_tensors(path: Path, device: torch.device | str) -> dict[str, torch.Tensor]:
    return load_file(str(path), device=str(device))
