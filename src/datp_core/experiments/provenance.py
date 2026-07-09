"""Artifact manifest dataclasses (docs/protocol/artifact_contracts.md #2).

Each manifest carries the identity fields that must match exactly before an
artifact may be reused instead of regenerated. Upstream artifacts are
referenced by ``manifest_id`` rather than duplicating their fields inline.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.datasets import DatasetId
from datp_core.domain.metrics import Metric
from datp_core.domain.partitions import SplitRole, SplitType
from datp_core.domain.policies import Comparator, ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime


class ArtifactStatus(StrEnum):
    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


class StatisticsMethod(StrEnum):
    BOOTSTRAP_BCA_AND_PAIRED_TESTS = "bootstrap_bca_and_paired_tests"


class RunStage(StrEnum):
    SCORING = "scoring"


@dataclass(frozen=True)
class ArtifactCommon:
    artifact_path: str
    created_at: str
    """ISO 8601 timestamp string."""
    code_version: str
    """Identifier for the code state that produced the artifact."""
    status: ArtifactStatus


def _require(value: str, field_name: str, owner: str) -> None:
    if not value:
        raise ValueError(f"{owner} must not omit {field_name}")


@dataclass(frozen=True)
class DatasetManifest:
    manifest_id: str
    dataset_id: DatasetId
    content_hash: str
    common: ArtifactCommon

    def __post_init__(self) -> None:
        _require(self.content_hash, "content_hash", "DatasetManifest")


@dataclass(frozen=True)
class PreprocessingManifest:
    manifest_id: str
    dataset_id: DatasetId
    preprocessing_contract_version: str
    raw_dataset_manifest_id: str
    common: ArtifactCommon

    def __post_init__(self) -> None:
        _require(self.raw_dataset_manifest_id, "raw_dataset_manifest_id", "PreprocessingManifest")


@dataclass(frozen=True)
class SplitManifest:
    manifest_id: str
    dataset_id: DatasetId
    regime: Regime
    split_policy: SplitType
    seed: int
    preprocessing_manifest_id: str
    common: ArtifactCommon

    def __post_init__(self) -> None:
        _require(self.preprocessing_manifest_id, "preprocessing_manifest_id", "SplitManifest")


@dataclass(frozen=True)
class CheckpointManifest:
    manifest_id: str
    dataset_id: DatasetId
    regime: Regime
    seed: int
    training_algorithm: TrainingAlgorithm
    selected_round: int
    checkpoint_selection_rule: str
    weight_hash: str
    split_manifest_id: str
    common: ArtifactCommon
    alpha: float | None

    def __post_init__(self) -> None:
        _require(self.split_manifest_id, "split_manifest_id", "CheckpointManifest")
        _require(self.weight_hash, "weight_hash", "CheckpointManifest")


@dataclass(frozen=True)
class ScoreManifest:
    manifest_id: str
    dataset_id: DatasetId
    regime: Regime
    seed: int
    checkpoint_manifest_id: str
    split_role: SplitRole
    common: ArtifactCommon

    def __post_init__(self) -> None:
        _require(self.checkpoint_manifest_id, "checkpoint_manifest_id", "ScoreManifest")


@dataclass(frozen=True)
class ThresholdManifest:
    manifest_id: str
    policy: ThresholdPolicy | Comparator
    dataset_id: DatasetId
    regime: Regime
    seed: int
    score_manifest_id: str
    config_hash: str
    common: ArtifactCommon

    def __post_init__(self) -> None:
        _require(self.score_manifest_id, "score_manifest_id", "ThresholdManifest")
        _require(self.config_hash, "config_hash", "ThresholdManifest")


@dataclass(frozen=True)
class MetricManifest:
    manifest_id: str
    metric: Metric
    dataset_id: DatasetId
    regime: Regime
    seed: int
    threshold_manifest_id: str
    common: ArtifactCommon

    def __post_init__(self) -> None:
        _require(self.threshold_manifest_id, "threshold_manifest_id", "MetricManifest")


@dataclass(frozen=True)
class StatisticsManifest:
    manifest_id: str
    method: StatisticsMethod
    dataset_id: DatasetId
    regime: Regime
    per_seed_metric_manifest_ids: tuple[str, ...]
    common: ArtifactCommon

    def __post_init__(self) -> None:
        if not self.per_seed_metric_manifest_ids:
            raise ValueError("StatisticsManifest must not omit per_seed_metric_manifest_ids")


@dataclass(frozen=True)
class TableManifest:
    manifest_id: str
    experiment_id: str
    source_artifact_ids: tuple[str, ...]
    common: ArtifactCommon

    def __post_init__(self) -> None:
        if not self.source_artifact_ids:
            raise ValueError("TableManifest must not omit source_artifact_ids")


@dataclass(frozen=True)
class FigureManifest:
    manifest_id: str
    experiment_id: str
    source_artifact_ids: tuple[str, ...]
    common: ArtifactCommon

    def __post_init__(self) -> None:
        if not self.source_artifact_ids:
            raise ValueError("FigureManifest must not omit source_artifact_ids")


@dataclass(frozen=True)
class RunManifest:
    manifest_id: str
    stage_name: RunStage
    config_snapshot_id: str
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    common: ArtifactCommon

    def __post_init__(self) -> None:
        _require(self.config_snapshot_id, "config_snapshot_id", "RunManifest")


@dataclass(frozen=True)
class CuratedResultManifest:
    manifest_id: str
    experiment_id: str
    claim_tier: int
    source_raw_artifact_id: str
    common: ArtifactCommon

    def __post_init__(self) -> None:
        _require(self.source_raw_artifact_id, "source_raw_artifact_id", "CuratedResultManifest")
