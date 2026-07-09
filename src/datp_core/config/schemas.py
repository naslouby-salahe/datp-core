"""Typed config-document schemas for the five config groups (configs/*)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from datp_core.domain.clients import ClientIdentityType
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import Comparator, ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime


class ConfigStatus(StrEnum):
    """Readiness of a config skeleton; Phase 1 configs never exceed IMPLEMENTATION_PENDING."""

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


DATASET_REGIME_COMPATIBILITY: dict[DatasetId, tuple[Regime, ...]] = {
    DatasetId.N_BAIOT: (Regime.A, Regime.C),
    DatasetId.CICIOT2023: (Regime.B_A, Regime.B_B_REJECTED_NO_METADATA),
    DatasetId.EDGE_IIOTSET: (Regime.D, Regime.D_TEMPORAL),
}
"""docs/protocol/artifact_contracts.md #1 regime-compatibility column, per dataset id."""


@dataclass(frozen=True)
class DatasetConfig:
    name: str
    status: ConfigStatus
    dataset_id: DatasetId
    regimes: tuple[Regime, ...]
    raw_subdirectory: str
    client_identity_type: ClientIdentityType | None = None
    """None only when every listed regime has RegimeRole.REJECTED (no invented device identity, SB-28)."""


@dataclass(frozen=True)
class ModelArchitectureConfig:
    """Dataset-agnostic encoder/decoder shape contract (e.g. configs/training/base_autoencoder.yaml).

    Concrete layer sizes are a Phase 2+ decision; Phase 1 only fixes the
    architecture family identity so downstream training configs can reference it.
    """

    name: str
    status: ConfigStatus
    architecture_family: ArchitectureFamily


@dataclass(frozen=True)
class TrainingConfig:
    name: str
    status: ConfigStatus
    dataset_id: DatasetId
    training_algorithm: TrainingAlgorithm
    seed_plan: tuple[int, ...]


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

    @property
    def is_runnable(self) -> bool:
        """Phase 1 never exposes a suite runner; no suite reaches READY_FOR_FULL_RUN yet."""
        return self.status is ConfigStatus.READY_FOR_FULL_RUN
