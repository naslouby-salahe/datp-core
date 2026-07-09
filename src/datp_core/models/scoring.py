"""Frozen-checkpoint reconstruction scoring and score-reuse lineage validation."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from datp_core.data.splits import RegimeASplits
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import TrainingAlgorithm
from datp_core.domain.regimes import Regime
from datp_core.models.frozen import FrozenAutoencoder


class ScoreArtifactError(RuntimeError):
    """Raised when score generation or score artifact reuse violates lineage."""


SCORE_CONTRACT_ID = "anchor_reconstruction_scores_v1"
JSON_SUFFIX = ".json"


@dataclass(frozen=True)
class ClientScoreSet:
    client_id: str
    calibration_benign: np.ndarray
    test_benign: np.ndarray
    test_attack: np.ndarray
    calibration_eligible: bool

    def __post_init__(self) -> None:
        for scores in (self.calibration_benign, self.test_benign, self.test_attack):
            if scores.ndim != 1:
                raise ScoreArtifactError("reconstruction score arrays must be one-dimensional")
            scores.setflags(write=False)


@dataclass(frozen=True)
class ScoreArtifactManifest:
    score_id: str
    dataset_id: DatasetId
    regime: Regime
    client_mapping_id: str
    split_id: str
    preprocessing_id: str
    checkpoint_id: str
    model_architecture_id: str
    training_algorithm: TrainingAlgorithm
    seed: int
    score_contract_id: str
    client_calibration_eligibility: tuple[tuple[str, bool], ...]


@dataclass(frozen=True)
class AnchorScoreArtifact:
    manifest: ScoreArtifactManifest
    clients: tuple[ClientScoreSet, ...]


def _reconstruction_scores(model: FrozenAutoencoder, features: np.ndarray) -> np.ndarray:
    return np.mean((model.reconstruct(features) - features) ** 2, axis=1)


def generate_anchor_scores(
    frozen_model: FrozenAutoencoder,
    splits: RegimeASplits,
    *,
    client_mapping_id: str,
    preprocessing_id: str,
) -> AnchorScoreArtifact:
    if frozen_model.manifest.split_id != splits.split_config_hash:
        raise ScoreArtifactError("frozen checkpoint split identity does not match score split")
    clients = tuple(
        ClientScoreSet(
            client_id=client.client_id,
            calibration_benign=_reconstruction_scores(frozen_model, client.calibration.features),
            test_benign=_reconstruction_scores(frozen_model, client.test_benign.features),
            test_attack=_reconstruction_scores(frozen_model, client.test_attack.features),
            calibration_eligible=client.calibration_eligible,
        )
        for client in splits.clients
    )
    manifest = ScoreArtifactManifest(
        score_id=f"scores-{frozen_model.manifest.checkpoint_id}",
        dataset_id=frozen_model.manifest.dataset_id,
        regime=frozen_model.manifest.regime,
        client_mapping_id=client_mapping_id,
        split_id=splits.split_config_hash,
        preprocessing_id=preprocessing_id,
        checkpoint_id=frozen_model.manifest.checkpoint_id,
        model_architecture_id=frozen_model.manifest.architecture_id,
        training_algorithm=frozen_model.manifest.training_algorithm,
        seed=frozen_model.manifest.seed,
        score_contract_id=SCORE_CONTRACT_ID,
        client_calibration_eligibility=tuple((client.client_id, client.calibration_eligible) for client in clients),
    )
    return AnchorScoreArtifact(manifest=manifest, clients=clients)


def validate_score_reuse(existing: ScoreArtifactManifest, requested: ScoreArtifactManifest) -> None:
    fields = (
        "dataset_id",
        "regime",
        "client_mapping_id",
        "split_id",
        "preprocessing_id",
        "checkpoint_id",
        "model_architecture_id",
        "training_algorithm",
        "seed",
        "score_contract_id",
    )
    mismatched = [field for field in fields if getattr(existing, field) != getattr(requested, field)]
    if mismatched:
        raise ScoreArtifactError(f"score artifact reuse rejected; mismatched fields: {', '.join(mismatched)}")


def write_score_artifact(artifact: AnchorScoreArtifact, path: Path) -> None:
    if path.exists() or path.with_suffix(JSON_SUFFIX).exists():
        raise ScoreArtifactError(f"refusing to overwrite existing score artifact {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {}
    for client in artifact.clients:
        arrays[f"{client.client_id}__calibration"] = client.calibration_benign
        arrays[f"{client.client_id}__test_benign"] = client.test_benign
        arrays[f"{client.client_id}__test_attack"] = client.test_attack
    compressed_writer = cast(Any, np.savez_compressed)
    compressed_writer(str(path), **arrays)
    path.with_suffix(JSON_SUFFIX).write_text(
        json.dumps(asdict(artifact.manifest), default=str, indent=2, sort_keys=True)
    )


def read_score_artifact(path: Path) -> AnchorScoreArtifact:
    manifest_path = path.with_suffix(JSON_SUFFIX)
    if not path.is_file() or not manifest_path.is_file():
        raise ScoreArtifactError(f"score artifact and manifest are both required: {path}")
    data = json.loads(manifest_path.read_text())
    manifest = ScoreArtifactManifest(
        score_id=data["score_id"],
        dataset_id=DatasetId(data["dataset_id"]),
        regime=Regime(data["regime"]),
        client_mapping_id=data["client_mapping_id"],
        split_id=data["split_id"],
        preprocessing_id=data["preprocessing_id"],
        checkpoint_id=data["checkpoint_id"],
        model_architecture_id=data["model_architecture_id"],
        training_algorithm=TrainingAlgorithm(data["training_algorithm"]),
        seed=int(data["seed"]),
        score_contract_id=data["score_contract_id"],
        client_calibration_eligibility=tuple(
            (str(client_id), bool(eligible)) for client_id, eligible in data["client_calibration_eligibility"]
        ),
    )
    clients: list[ClientScoreSet] = []
    with np.load(path) as arrays:
        for client_id, eligible in sorted(manifest.client_calibration_eligibility):
            clients.append(
                ClientScoreSet(
                    client_id=client_id,
                    calibration_benign=arrays[f"{client_id}__calibration"].copy(),
                    test_benign=arrays[f"{client_id}__test_benign"].copy(),
                    test_attack=arrays[f"{client_id}__test_attack"].copy(),
                    calibration_eligible=eligible,
                )
            )
    return AnchorScoreArtifact(manifest=manifest, clients=tuple(clients))
