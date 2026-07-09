"""Manifest read/write helpers and reuse-identity guards.

Manifests round-trip through JSON; every ``from_*`` function reconstructs the
exact typed dataclass ``to_*`` started from, including enum fields.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from datp_core.domain.datasets import DatasetId
from datp_core.domain.metrics import Metric
from datp_core.domain.partitions import SplitRole, SplitType
from datp_core.domain.policies import Comparator, ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime

from .provenance import (
    ArtifactCommon,
    ArtifactStatus,
    CheckpointManifest,
    CuratedResultManifest,
    DatasetManifest,
    FigureManifest,
    MetricManifest,
    PreprocessingManifest,
    RunManifest,
    RunStage,
    ScoreManifest,
    SplitManifest,
    StatisticsManifest,
    StatisticsMethod,
    TableManifest,
    ThresholdManifest,
)


class ManifestReuseError(RuntimeError):
    """Raised when a requested reuse identity does not match an existing manifest."""


def _common_from_dict(data: dict[str, Any]) -> ArtifactCommon:
    return ArtifactCommon(
        artifact_path=data["artifact_path"],
        created_at=data["created_at"],
        code_version=data["code_version"],
        status=ArtifactStatus(data["status"]),
    )


def _parse_policy(value: str) -> ThresholdPolicy | Comparator:
    try:
        return ThresholdPolicy(value)
    except ValueError:
        return Comparator(value)


def manifest_to_dict(manifest: Any) -> dict[str, Any]:
    return asdict(manifest)


def manifest_to_json(manifest: Any) -> str:
    return json.dumps(manifest_to_dict(manifest), indent=2, sort_keys=True)


def write_manifest(manifest: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(manifest_to_json(manifest))


def dataset_manifest_from_dict(data: dict[str, Any]) -> DatasetManifest:
    return DatasetManifest(
        manifest_id=data["manifest_id"],
        dataset_id=DatasetId(data["dataset_id"]),
        content_hash=data["content_hash"],
        common=_common_from_dict(data["common"]),
    )


def preprocessing_manifest_from_dict(data: dict[str, Any]) -> PreprocessingManifest:
    return PreprocessingManifest(
        manifest_id=data["manifest_id"],
        dataset_id=DatasetId(data["dataset_id"]),
        preprocessing_contract_version=data["preprocessing_contract_version"],
        raw_dataset_manifest_id=data["raw_dataset_manifest_id"],
        common=_common_from_dict(data["common"]),
    )


def split_manifest_from_dict(data: dict[str, Any]) -> SplitManifest:
    return SplitManifest(
        manifest_id=data["manifest_id"],
        dataset_id=DatasetId(data["dataset_id"]),
        regime=Regime(data["regime"]),
        split_policy=SplitType(data["split_policy"]),
        seed=data["seed"],
        preprocessing_manifest_id=data["preprocessing_manifest_id"],
        common=_common_from_dict(data["common"]),
    )


def checkpoint_manifest_from_dict(data: dict[str, Any]) -> CheckpointManifest:
    return CheckpointManifest(
        manifest_id=data["manifest_id"],
        dataset_id=DatasetId(data["dataset_id"]),
        regime=Regime(data["regime"]),
        seed=data["seed"],
        training_algorithm=TrainingAlgorithm(data["training_algorithm"]),
        selected_round=data["selected_round"],
        checkpoint_selection_rule=data["checkpoint_selection_rule"],
        weight_hash=data["weight_hash"],
        split_manifest_id=data["split_manifest_id"],
        common=_common_from_dict(data["common"]),
        alpha=data.get("alpha"),
    )


def score_manifest_from_dict(data: dict[str, Any]) -> ScoreManifest:
    return ScoreManifest(
        manifest_id=data["manifest_id"],
        dataset_id=DatasetId(data["dataset_id"]),
        regime=Regime(data["regime"]),
        seed=data["seed"],
        checkpoint_manifest_id=data["checkpoint_manifest_id"],
        split_role=SplitRole(data["split_role"]),
        common=_common_from_dict(data["common"]),
    )


def threshold_manifest_from_dict(data: dict[str, Any]) -> ThresholdManifest:
    return ThresholdManifest(
        manifest_id=data["manifest_id"],
        policy=_parse_policy(data["policy"]),
        dataset_id=DatasetId(data["dataset_id"]),
        regime=Regime(data["regime"]),
        seed=data["seed"],
        score_manifest_id=data["score_manifest_id"],
        config_hash=data["config_hash"],
        common=_common_from_dict(data["common"]),
    )


def metric_manifest_from_dict(data: dict[str, Any]) -> MetricManifest:
    return MetricManifest(
        manifest_id=data["manifest_id"],
        metric=Metric(data["metric"]),
        dataset_id=DatasetId(data["dataset_id"]),
        regime=Regime(data["regime"]),
        seed=data["seed"],
        threshold_manifest_id=data["threshold_manifest_id"],
        common=_common_from_dict(data["common"]),
    )


def statistics_manifest_from_dict(data: dict[str, Any]) -> StatisticsManifest:
    return StatisticsManifest(
        manifest_id=data["manifest_id"],
        method=StatisticsMethod(data["method"]),
        dataset_id=DatasetId(data["dataset_id"]),
        regime=Regime(data["regime"]),
        per_seed_metric_manifest_ids=tuple(data["per_seed_metric_manifest_ids"]),
        common=_common_from_dict(data["common"]),
    )


def table_manifest_from_dict(data: dict[str, Any]) -> TableManifest:
    return TableManifest(
        manifest_id=data["manifest_id"],
        experiment_id=data["experiment_id"],
        source_artifact_ids=tuple(data["source_artifact_ids"]),
        common=_common_from_dict(data["common"]),
    )


def figure_manifest_from_dict(data: dict[str, Any]) -> FigureManifest:
    return FigureManifest(
        manifest_id=data["manifest_id"],
        experiment_id=data["experiment_id"],
        source_artifact_ids=tuple(data["source_artifact_ids"]),
        common=_common_from_dict(data["common"]),
    )


def run_manifest_from_dict(data: dict[str, Any]) -> RunManifest:
    return RunManifest(
        manifest_id=data["manifest_id"],
        stage_name=RunStage(data["stage_name"]),
        config_snapshot_id=data["config_snapshot_id"],
        inputs=tuple(data["inputs"]),
        outputs=tuple(data["outputs"]),
        common=_common_from_dict(data["common"]),
    )


def curated_result_manifest_from_dict(data: dict[str, Any]) -> CuratedResultManifest:
    return CuratedResultManifest(
        manifest_id=data["manifest_id"],
        experiment_id=data["experiment_id"],
        claim_tier=data["claim_tier"],
        source_raw_artifact_id=data["source_raw_artifact_id"],
        common=_common_from_dict(data["common"]),
    )


_FROM_DICT_BY_TYPE_NAME: dict[str, Any] = {
    "DatasetManifest": dataset_manifest_from_dict,
    "PreprocessingManifest": preprocessing_manifest_from_dict,
    "SplitManifest": split_manifest_from_dict,
    "CheckpointManifest": checkpoint_manifest_from_dict,
    "ScoreManifest": score_manifest_from_dict,
    "ThresholdManifest": threshold_manifest_from_dict,
    "MetricManifest": metric_manifest_from_dict,
    "StatisticsManifest": statistics_manifest_from_dict,
    "TableManifest": table_manifest_from_dict,
    "FigureManifest": figure_manifest_from_dict,
    "RunManifest": run_manifest_from_dict,
    "CuratedResultManifest": curated_result_manifest_from_dict,
}


def read_manifest(path: Path, manifest_type: type) -> Any:
    data = json.loads(path.read_text())
    return _FROM_DICT_BY_TYPE_NAME[manifest_type.__name__](data)


def verify_score_manifest_reuse(
    existing: ScoreManifest,
    dataset_id: DatasetId,
    regime: Regime,
    seed: int,
    checkpoint_manifest_id: str,
) -> None:
    """docs/protocol/artifact_contracts.md #2: score reuse-validity key."""
    requested = (dataset_id, regime, seed, checkpoint_manifest_id)
    actual = (existing.dataset_id, existing.regime, existing.seed, existing.checkpoint_manifest_id)
    if requested != actual:
        raise ManifestReuseError(
            f"score manifest {existing.manifest_id} identity {actual} does not match "
            f"requested reuse identity {requested}"
        )


def verify_checkpoint_manifest_reuse(
    existing: CheckpointManifest,
    dataset_id: DatasetId,
    regime: Regime,
    seed: int,
    alpha: float | None,
) -> None:
    """docs/protocol/artifact_contracts.md #2: frozen-checkpoint reuse-validity key."""
    requested = (dataset_id, regime, seed, alpha)
    actual = (existing.dataset_id, existing.regime, existing.seed, existing.alpha)
    if requested != actual:
        raise ManifestReuseError(
            f"checkpoint manifest {existing.manifest_id} identity {actual} does not match "
            f"requested reuse identity {requested}"
        )
