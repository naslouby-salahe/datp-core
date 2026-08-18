import os

import torch


def _select_learning_device() -> torch.device:
    configured = os.environ.get("DATP_LEARNING_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(configured)
    if device.type == "cuda" and device.index is None:
        return torch.device("cuda", torch.cuda.current_device())
    return device


LEARNING_DEVICE: torch.device = _select_learning_device()


def _select_training_device() -> torch.device:
    configured = os.environ.get("DATP_TRAINING_DEVICE", "cpu")
    device = torch.device(configured)
    if device.type == "cuda" and device.index is None:
        return torch.device("cuda", torch.cuda.current_device())
    return device


TRAINING_DEVICE: torch.device = _select_training_device()
