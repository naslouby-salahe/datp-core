"""YAML config-document loading into typed dataclasses (see schemas.py)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from datp_core.domain.clients import ClientIdentityType
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import Comparator, ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime

from .schemas import (
    AnalysisConfig,
    AnalysisKind,
    ArchitectureFamily,
    CalibrationLabelScope,
    ConfigStatus,
    DatasetConfig,
    ModelArchitectureConfig,
    SuiteConfig,
    ThresholdingConfig,
    TrainingConfig,
)
from .validation import (
    ConfigLoadError,
    validate_benign_only_calibration,
    validate_client_identity_presence,
    validate_dataset_regime_pair,
    validate_policies_nonempty,
    validate_q_values,
    validate_seed_plan,
    validate_suite_training_flag,
    validate_threshold_policy_scope,
)

_DATASET_FIELDS = {"name", "status", "dataset_id", "regimes", "client_identity_type", "raw_subdirectory"}
_MODEL_ARCHITECTURE_FIELDS = {"name", "status", "architecture_family"}
_TRAINING_FIELDS = {"name", "status", "dataset_id", "training_algorithm", "seed_plan"}
_THRESHOLDING_FIELDS = {
    "name",
    "status",
    "policies",
    "q_values",
    "has_family_taxonomy",
    "cluster_k",
    "calibration_label_scope",
}
_ANALYSIS_FIELDS = {"name", "status", "analysis_kind"}
_SUITE_FIELDS = {
    "name",
    "status",
    "regimes",
    "experiment_ids",
    "training_enabled",
    "requires_score_reuse",
    "allow_training_override",
}


def load_yaml_document(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ConfigLoadError(f"{path}: config document must be a YAML mapping")
    return data


def _reject_unknown_fields(data: dict[str, Any], allowed: set[str], path: Path) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ConfigLoadError(f"{path}: unknown field(s) {sorted(unknown)}")


def _require_bool(data: dict[str, Any], field_name: str, path: Path) -> bool:
    value = data[field_name]
    if not isinstance(value, bool):
        raise ConfigLoadError(f"{path}: {field_name} must be a YAML boolean")
    return value


def _parse_policy(value: str, path: Path) -> ThresholdPolicy | Comparator:
    try:
        return ThresholdPolicy(value)
    except ValueError:
        pass
    try:
        return Comparator(value)
    except ValueError as exc:
        raise ConfigLoadError(f"{path}: unknown threshold policy/comparator {value!r}") from exc


def load_dataset_config(path: Path) -> DatasetConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _DATASET_FIELDS, path)
    try:
        dataset_id = DatasetId(data["dataset_id"])
        regimes = tuple(Regime(r) for r in data["regimes"])
        raw_identity = data.get("client_identity_type")
        client_identity_type = ClientIdentityType(raw_identity) if raw_identity is not None else None
        status = ConfigStatus(data["status"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    for regime in regimes:
        validate_dataset_regime_pair(dataset_id, regime)
    validate_client_identity_presence(status, client_identity_type)
    return DatasetConfig(
        name=data["name"],
        status=status,
        dataset_id=dataset_id,
        regimes=regimes,
        client_identity_type=client_identity_type,
        raw_subdirectory=data["raw_subdirectory"],
    )


def load_model_architecture_config(path: Path) -> ModelArchitectureConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _MODEL_ARCHITECTURE_FIELDS, path)
    try:
        status = ConfigStatus(data["status"])
        architecture_family = ArchitectureFamily(data["architecture_family"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    return ModelArchitectureConfig(
        name=data["name"], status=status, architecture_family=architecture_family
    )


def load_training_config(path: Path) -> TrainingConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _TRAINING_FIELDS, path)
    try:
        dataset_id = DatasetId(data["dataset_id"])
        training_algorithm = TrainingAlgorithm(data["training_algorithm"])
        status = ConfigStatus(data["status"])
        seed_plan = tuple(data["seed_plan"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    validate_seed_plan(seed_plan)
    return TrainingConfig(
        name=data["name"],
        status=status,
        dataset_id=dataset_id,
        training_algorithm=training_algorithm,
        seed_plan=seed_plan,
    )


def load_thresholding_config(path: Path) -> ThresholdingConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _THRESHOLDING_FIELDS, path)
    try:
        status = ConfigStatus(data["status"])
        policies = tuple(_parse_policy(p, path) for p in data["policies"])
        q_values = tuple(float(q) for q in data["q_values"])
        calibration_label_scope = CalibrationLabelScope(data["calibration_label_scope"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    has_family_taxonomy = (
        _require_bool(data, "has_family_taxonomy", path) if "has_family_taxonomy" in data else None
    )
    cluster_k = data.get("cluster_k")
    if cluster_k is not None and type(cluster_k) is not int:
        raise ConfigLoadError(f"{path}: cluster_k must be an integer when present")

    validate_policies_nonempty(policies)
    validate_q_values(q_values)
    for policy in policies:
        validate_threshold_policy_scope(policy, has_family_taxonomy, cluster_k)
        validate_benign_only_calibration(policy, calibration_label_scope)

    return ThresholdingConfig(
        name=data["name"],
        status=status,
        policies=policies,
        q_values=q_values,
        has_family_taxonomy=has_family_taxonomy,
        cluster_k=cluster_k,
        calibration_label_scope=calibration_label_scope,
    )


def load_analysis_config(path: Path) -> AnalysisConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _ANALYSIS_FIELDS, path)
    try:
        status = ConfigStatus(data["status"])
        analysis_kind = AnalysisKind(data["analysis_kind"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    return AnalysisConfig(name=data["name"], status=status, analysis_kind=analysis_kind)


def load_suite_config(path: Path) -> SuiteConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _SUITE_FIELDS, path)
    try:
        status = ConfigStatus(data["status"])
        regimes = tuple(Regime(r) for r in data["regimes"])
        experiment_ids = tuple(data["experiment_ids"])
        training_enabled = _require_bool(data, "training_enabled", path)
        requires_score_reuse = _require_bool(data, "requires_score_reuse", path)
        allow_training_override = _require_bool(data, "allow_training_override", path)
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    if not regimes:
        raise ConfigLoadError(f"{path}: regimes must not be empty")

    validate_suite_training_flag(training_enabled, requires_score_reuse, allow_training_override)

    return SuiteConfig(
        name=data["name"],
        status=status,
        regimes=regimes,
        experiment_ids=experiment_ids,
        training_enabled=training_enabled,
        requires_score_reuse=requires_score_reuse,
        allow_training_override=allow_training_override,
    )
