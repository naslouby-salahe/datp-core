"""Model tensor persistence using SafeTensors."""

from __future__ import annotations

from pathlib import Path

import torch
from safetensors.torch import load_file, save_file


def save_model_safetensors(model_state_dict: dict[str, torch.Tensor], target_path: Path) -> None:
    clean_tensors = {k: v.cpu().contiguous() for k, v in model_state_dict.items()}
    target_path.parent.mkdir(parents=True, exist_ok=True)
    save_file(clean_tensors, str(target_path))


def load_model_safetensors(target_path: Path) -> dict[str, torch.Tensor]:
    if not target_path.exists():
        raise FileNotFoundError(f"SafeTensors model file not found: {target_path}")
    return load_file(str(target_path))
