"""Frozen-checkpoint reconstruction scoring and score-reuse lineage validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np

from datp_core.data.splits import RegimeASplits
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import TrainingAlgorithm
from datp_core.domain.regimes import Regime
from datp_core.experiments.artifacts import write_manifest
from datp_core.models.autoencoder import Autoencoder
from datp_core.models.checkpoints import AnchorCheckpointManifest


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
        if not self.client_id:
            raise ScoreArtifactError("score sets require a client ID")
        for scores in (self.calibration_benign, self.test_benign, self.test_attack):
            if scores.ndim != 1 or not len(scores) or not np.all(np.isfinite(scores)) or np.any(scores < 0.0):
                raise ScoreArtifactError("reconstruction scores must be non-empty, finite, non-negative vectors")
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

    def __post_init__(self) -> None:
        provenance = (
            self.score_id,
            self.client_mapping_id,
            self.split_id,
            self.preprocessing_id,
            self.checkpoint_id,
            self.model_architecture_id,
            self.score_contract_id,
        )
        if not all(provenance):
            raise ScoreArtifactError("score manifest requires complete provenance")
        if self.seed < 0:
            raise ScoreArtifactError("score manifest seed must not be negative")
        if self.score_contract_id != SCORE_CONTRACT_ID:
            raise ScoreArtifactError("score manifest has an unexpected score contract ID")
        client_ids = tuple(client_id for client_id, _ in self.client_calibration_eligibility)
        if not client_ids or len(client_ids) != len(set(client_ids)) or any(not client_id for client_id in client_ids):
            raise ScoreArtifactError("score manifest requires unique non-empty client eligibility entries")


@dataclass(frozen=True)
class AnchorScoreArtifact:
    manifest: ScoreArtifactManifest
    clients: tuple[ClientScoreSet, ...]

    def __post_init__(self) -> None:
        client_ids = tuple(client.client_id for client in self.clients)
        eligibility = tuple((client.client_id, client.calibration_eligible) for client in self.clients)
        if not client_ids or len(client_ids) != len(set(client_ids)):
            raise ScoreArtifactError("score artifact requires unique client score sets")
        if eligibility != self.manifest.client_calibration_eligibility:
            raise ScoreArtifactError("score artifact clients do not match manifest calibration eligibility")


def _reconstruction_scores(model: Autoencoder, features: np.ndarray) -> np.ndarray:
    return np.mean((model.reconstruct(features) - features) ** 2, axis=1)


def generate_anchor_scores(
    model: Autoencoder,
    checkpoint_manifest: AnchorCheckpointManifest,
    splits: RegimeASplits,
    *,
    client_mapping_id: str,
    preprocessing_id: str,
) -> AnchorScoreArtifact:
    if not model.frozen:
        raise ScoreArtifactError("anchor scores require a frozen checkpoint model")
    if checkpoint_manifest.split_id != splits.split_config_hash:
        raise ScoreArtifactError("frozen checkpoint split identity does not match score split")
    clients = tuple(
        ClientScoreSet(
            client_id=client.client_id,
            calibration_benign=_reconstruction_scores(model, client.calibration.features),
            test_benign=_reconstruction_scores(model, client.test_benign.features),
            test_attack=_reconstruction_scores(model, client.test_attack.features),
            calibration_eligible=client.calibration_eligible,
        )
        for client in splits.clients
    )
    manifest = ScoreArtifactManifest(
        score_id=f"scores-{checkpoint_manifest.checkpoint_id}",
        dataset_id=checkpoint_manifest.dataset_id,
        regime=checkpoint_manifest.regime,
        client_mapping_id=client_mapping_id,
        split_id=splits.split_config_hash,
        preprocessing_id=preprocessing_id,
        checkpoint_id=checkpoint_manifest.checkpoint_id,
        model_architecture_id=checkpoint_manifest.architecture_id,
        training_algorithm=checkpoint_manifest.training_algorithm,
        seed=checkpoint_manifest.seed,
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
    write_manifest(artifact.manifest, path.with_suffix(JSON_SUFFIX))


def read_score_artifact(path: Path) -> AnchorScoreArtifact:
    manifest_path = path.with_suffix(JSON_SUFFIX)
    if not path.is_file() or not manifest_path.is_file():
        raise ScoreArtifactError(f"score artifact and manifest are both required: {path}")
    try:
        data = json.loads(manifest_path.read_text())
        if not isinstance(data, dict):
            raise TypeError("score manifest must be a JSON object")
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
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ScoreArtifactError(f"invalid score manifest {manifest_path}") from exc
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
