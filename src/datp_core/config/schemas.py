"""Typed config-document schemas for the five config groups (configs/*)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.clients import ClientIdentityType
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import Comparator, ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime
from datp_core.utils.hardware import DeviceType


class ConfigStatus(StrEnum):
    """Readiness of a typed configuration for validation, smoke runs, or operator-gated execution."""

    CONTRACT_ONLY = "contract_only"
    IMPLEMENTATION_PENDING = "implementation_pending"
    READY_FOR_SMOKE = "ready_for_smoke"
    READY_FOR_FULL_RUN = "ready_for_full_run"


class ConfigGroup(StrEnum):
    DATASET = "dataset"
    TRAINING = "training"
    THRESHOLDING = "thresholding"
    ANALYSIS = "analysis"
    SUITE = "suite"


class ArchitectureFamily(StrEnum):
    AUTOENCODER = "autoencoder"


class CalibrationLabelScope(StrEnum):
    BENIGN_ONLY = "benign_only"


class AnalysisKind(StrEnum):
    ABSORPTION_BANDS = "absorption_bands"
    BOOTSTRAP_BCA_AND_PAIRED_TESTS = "bootstrap_bca_and_paired_tests"
    MECHANISM_ANALYSIS = "mechanism_analysis"
    TABLE_AND_FIGURE_EXPORT = "table_and_figure_export"


@dataclass(frozen=True)
class AnchorArtifactLayout:
    run_root_prefix: str
    seed_directory_prefix: str
    preprocessing_id_prefix: str
    client_map_filename: str
    split_manifest_filename: str
    checkpoint_filename: str
    score_filename: str
    summary_filename: str
    threshold_filename: str


@dataclass(frozen=True)
class DatasetRegimeCompatibility:
    dataset_id: DatasetId
    regimes: tuple[Regime, ...]


DATASET_REGIME_COMPATIBILITIES: tuple[DatasetRegimeCompatibility, ...] = (
    DatasetRegimeCompatibility(DatasetId.N_BAIOT, (Regime.A, Regime.C)),
    DatasetRegimeCompatibility(DatasetId.CICIOT2023, (Regime.B_A, Regime.B_B_REJECTED_NO_METADATA)),
    DatasetRegimeCompatibility(DatasetId.EDGE_IIOTSET, (Regime.D, Regime.D_TEMPORAL)),
)
"""docs/protocol/artifact_contracts.md #1 regime-compatibility column, per dataset id."""


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    status: ConfigStatus
    dataset_id: DatasetId
    regimes: tuple[Regime, ...]
    raw_subdirectory: str
    train_fraction: float | None
    calibration_fraction: float | None
    client_identity_type: ClientIdentityType | None


@dataclass(frozen=True)
class ModelArchitectureConfig:
    """Dataset-agnostic encoder/decoder shape contract (e.g. configs/training/base_autoencoder.yaml).

    Smoke-ready anchor configurations must name their fixed hidden width.
    """

    name: str
    status: ConfigStatus
    architecture_family: ArchitectureFamily
    hidden_dim: int | None


@dataclass(frozen=True)
class TrainingConfig:
    name: str
    status: ConfigStatus
    dataset_id: DatasetId
    training_algorithm: TrainingAlgorithm
    seed_plan: tuple[int, ...]
    rounds: int | None
    local_epochs: int | None
    learning_rate: float | None
    momentum: float | None
    weight_decay: float | None
    full_participation: bool | None
    device: DeviceType | None
    fixture_client_count: int | None
    fixture_benign_rows: int | None
    fixture_attack_rows: int | None
    fixture_feature_count: int | None
    fixture_benign_mean_step: float | None
    fixture_attack_mean: float | None
    fixture_feature_std: float | None


@dataclass(frozen=True)
class ThresholdingConfig:
    name: str
    status: ConfigStatus
    policies: tuple[ThresholdPolicy | Comparator, ...]
    q_values: tuple[float, ...]
    has_family_taxonomy: bool | None
    cluster_k: int | None
    calibration_label_scope: CalibrationLabelScope


@dataclass(frozen=True)
class AnalysisConfig:
    name: str
    status: ConfigStatus
    analysis_kind: AnalysisKind


@dataclass(frozen=True)
class SuiteConfig:
    name: str
    status: ConfigStatus
    regimes: tuple[Regime, ...]
    experiment_ids: tuple[str, ...]
    training_enabled: bool
    requires_score_reuse: bool
    allow_training_override: bool
    dataset_config: str | None
    training_config: str | None
    model_config: str | None
    thresholding_config: str | None
    mini_seed_count: int | None
    expected_client_count: int | None
    artifact_layout: AnchorArtifactLayout | None

    @property
    def is_runnable(self) -> bool:
        """Only a full-run-ready suite may run without an explicit development command."""
        return self.status is ConfigStatus.READY_FOR_FULL_RUN
