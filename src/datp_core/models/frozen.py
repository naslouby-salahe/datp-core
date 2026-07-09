"""Read-only checkpoint loading for scoring and threshold-only anchor stages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from datp_core.models.autoencoder import Autoencoder, ModelParameter
from datp_core.models.checkpoints import AnchorCheckpointManifest, CheckpointError, _weight_hash
from datp_core.utils.hardware import DeviceType


@dataclass(frozen=True)
class FrozenAutoencoder:
    model: Autoencoder
    manifest: AnchorCheckpointManifest

    def reconstruct(self, inputs: np.ndarray) -> np.ndarray:
        return self.model.reconstruct(inputs)


def load_frozen_anchor_checkpoint(
    path: Path, manifest: AnchorCheckpointManifest, *, device: DeviceType
) -> FrozenAutoencoder:
    if not path.is_file():
        raise CheckpointError(f"checkpoint file is missing: {path}")
    with np.load(path) as data:
        model = Autoencoder.initialize(
            int(data["input_dim"]),
            seed=manifest.seed,
            hidden_dim=int(data["hidden_dim"]),
            device=device,
        )
        model.load_numpy_parameters(
            tuple(
                ModelParameter(name=name, values=data[name])
                for name in data.files
                if name not in {"input_dim", "hidden_dim"}
            )
        )
    if model.architecture_id != manifest.architecture_id or _weight_hash(model) != manifest.weight_hash:
        raise CheckpointError("checkpoint weights or architecture do not match the frozen manifest")
    model.freeze()
    return FrozenAutoencoder(model=model, manifest=manifest)
