"""Checkpoint selection and immutable anchor checkpoint persistence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import TrainingAlgorithm
from datp_core.domain.regimes import Regime
from datp_core.experiments.artifacts import write_manifest
from datp_core.models.autoencoder import ARCHITECTURE_ID, Autoencoder, ModelParameter


class CheckpointError(RuntimeError):
    """Raised when anchor checkpoint lineage or selection is invalid."""


FINAL_ROUND_SELECTION_RULE = "final_training_round"


@dataclass(frozen=True)
class AnchorCheckpointManifest:
    checkpoint_id: str
    dataset_id: DatasetId
    regime: Regime
    seed: int
    split_id: str
    architecture_id: str
    training_algorithm: TrainingAlgorithm
    selected_round: int
    selection_rule: str
    weight_hash: str

    def __post_init__(self) -> None:
        if not all(
            (
                self.checkpoint_id,
                self.split_id,
                self.architecture_id,
                self.selection_rule,
                self.weight_hash,
            )
        ):
            raise CheckpointError("anchor checkpoint manifest requires complete provenance")
        if self.seed < 0 or self.selected_round < 1:
            raise CheckpointError("anchor checkpoint manifest requires a non-negative seed and positive selected round")
        if self.selection_rule != FINAL_ROUND_SELECTION_RULE:
            raise CheckpointError("anchor checkpoint selection must use the final training round")
        if "threshold" in self.selection_rule or "auroc" in self.selection_rule:
            raise CheckpointError("checkpoint selection must not reference threshold metrics or AUROC")


def _weight_hash(model: Autoencoder) -> str:
    digest = hashlib.sha256()
    for parameter in sorted(model.numpy_parameters(), key=lambda parameter: parameter.name):
        digest.update(parameter.name.encode())
        digest.update(parameter.values.tobytes())
    return digest.hexdigest()


def _checkpoint_npz_arrays(
    parameters: tuple[ModelParameter, ...], *, input_dim: int, hidden_dim: int
) -> dict[str, np.ndarray | int]:
    return {parameter.name: parameter.values for parameter in parameters} | {
        "input_dim": input_dim,
        "hidden_dim": hidden_dim,
    }


def save_anchor_checkpoint(
    model: Autoencoder,
    path: Path,
    *,
    dataset_id: DatasetId,
    regime: Regime,
    seed: int,
    split_id: str,
    selected_round: int,
) -> AnchorCheckpointManifest:
    if path.exists():
        raise CheckpointError(f"refusing to overwrite existing checkpoint {path}")
    if model.architecture_id != ARCHITECTURE_ID:
        raise CheckpointError("anchor checkpoint model has an unexpected architecture ID")
    path.parent.mkdir(parents=True, exist_ok=True)
    compressed_writer = cast(Any, np.savez_compressed)
    compressed_writer(
        str(path),
        **_checkpoint_npz_arrays(model.numpy_parameters(), input_dim=model.input_dim, hidden_dim=model.hidden_dim),
    )
    weight_hash = _weight_hash(model)
    manifest = AnchorCheckpointManifest(
        checkpoint_id=weight_hash[:16],
        dataset_id=dataset_id,
        regime=regime,
        seed=seed,
        split_id=split_id,
        architecture_id=model.architecture_id,
        training_algorithm=TrainingAlgorithm.FEDAVG,
        selected_round=selected_round,
        selection_rule=FINAL_ROUND_SELECTION_RULE,
        weight_hash=weight_hash,
    )
    write_manifest(manifest, path.with_suffix(".json"))
    path.chmod(0o444)
    path.with_suffix(".json").chmod(0o444)
    return manifest


def read_anchor_checkpoint_manifest(path: Path) -> AnchorCheckpointManifest:
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            raise TypeError("checkpoint manifest must be a JSON object")
        return AnchorCheckpointManifest(
            checkpoint_id=data["checkpoint_id"],
            dataset_id=DatasetId(data["dataset_id"]),
            regime=Regime(data["regime"]),
            seed=int(data["seed"]),
            split_id=data["split_id"],
            architecture_id=data["architecture_id"],
            training_algorithm=TrainingAlgorithm(data["training_algorithm"]),
            selected_round=int(data["selected_round"]),
            selection_rule=data["selection_rule"],
            weight_hash=data["weight_hash"],
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise CheckpointError(f"invalid anchor checkpoint manifest {path}") from exc
