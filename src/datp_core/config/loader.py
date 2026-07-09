"""YAML config-document loading into typed dataclasses (see schemas.py)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path
from typing import Any

import yaml

from datp_core.domain.clients import ClientIdentityType
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import Comparator, ThresholdPolicy, TrainingAlgorithm
from datp_core.domain.regimes import Regime
from datp_core.utils.hardware import DeviceType

from .schemas import (
    AnalysisConfig,
    AnalysisKind,
    AnchorArtifactLayout,
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
    validate_anchor_architecture_fields,
    validate_anchor_split_fields,
    validate_anchor_training_fields,
    validate_benign_only_calibration,
    validate_client_identity_presence,
    validate_dataset_regime_pair,
    validate_policies_nonempty,
    validate_q_values,
    validate_seed_plan,
    validate_suite_training_flag,
    validate_threshold_policy_scope,
)


def load_yaml_document(path: Path) -> Mapping[str, Any]:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ConfigLoadError(f"{path}: config document must be a YAML mapping")
    return data


def _reject_unknown_fields(data: Mapping[str, Any], allowed: frozenset[str], path: Path) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise ConfigLoadError(f"{path}: unknown field(s) {sorted(unknown)}")


def _schema_fields(schema_type: type) -> frozenset[str]:
    return frozenset(field.name for field in fields(schema_type))


def _require_bool(data: Mapping[str, Any], field_name: str, path: Path) -> bool:
    value = data[field_name]
    if not isinstance(value, bool):
        raise ConfigLoadError(f"{path}: {field_name} must be a YAML boolean")
    return value


def _optional_int(data: Mapping[str, Any], field_name: str, path: Path) -> int | None:
    value = data.get(field_name)
    if value is not None and type(value) is not int:
        raise ConfigLoadError(f"{path}: {field_name} must be an integer when present")
    return value


def _optional_float(data: Mapping[str, Any], field_name: str, path: Path) -> float | None:
    value = data.get(field_name)
    if value is not None and not isinstance(value, (float, int)):
        raise ConfigLoadError(f"{path}: {field_name} must be numeric when present")
    return None if value is None else float(value)


def _optional_device(data: Mapping[str, Any], path: Path) -> DeviceType | None:
    raw_device = data.get("device")
    try:
        return None if raw_device is None else DeviceType(raw_device)
    except ValueError as exc:
        raise ConfigLoadError(f"{path}: unknown device {raw_device!r}") from exc


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
    _reject_unknown_fields(data, _schema_fields(DatasetConfig), path)
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
    train_fraction = data.get("train_fraction")
    calibration_fraction = data.get("calibration_fraction")
    for field_name, value in (("train_fraction", train_fraction), ("calibration_fraction", calibration_fraction)):
        if value is not None and not isinstance(value, (float, int)):
            raise ConfigLoadError(f"{path}: {field_name} must be numeric when present")
    numeric_train_fraction = None if train_fraction is None else float(train_fraction)
    numeric_calibration_fraction = None if calibration_fraction is None else float(calibration_fraction)
    validate_anchor_split_fields(status, numeric_train_fraction, numeric_calibration_fraction)
    return DatasetConfig(
        name=data["name"],
        status=status,
        dataset_id=dataset_id,
        regimes=regimes,
        client_identity_type=client_identity_type,
        raw_subdirectory=data["raw_subdirectory"],
        train_fraction=numeric_train_fraction,
        calibration_fraction=numeric_calibration_fraction,
    )


def load_model_architecture_config(path: Path) -> ModelArchitectureConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _schema_fields(ModelArchitectureConfig), path)
    try:
        status = ConfigStatus(data["status"])
        architecture_family = ArchitectureFamily(data["architecture_family"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    hidden_dim = data.get("hidden_dim")
    if hidden_dim is not None and type(hidden_dim) is not int:
        raise ConfigLoadError(f"{path}: hidden_dim must be an integer when present")
    validate_anchor_architecture_fields(status, hidden_dim)
    return ModelArchitectureConfig(
        name=data["name"], status=status, architecture_family=architecture_family, hidden_dim=hidden_dim
    )


def load_training_config(path: Path) -> TrainingConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _schema_fields(TrainingConfig), path)
    try:
        dataset_id = DatasetId(data["dataset_id"])
        training_algorithm = TrainingAlgorithm(data["training_algorithm"])
        status = ConfigStatus(data["status"])
        seed_plan = tuple(data["seed_plan"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    validate_seed_plan(seed_plan)
    rounds = _optional_int(data, "rounds", path)
    local_epochs = _optional_int(data, "local_epochs", path)
    numeric_learning_rate = _optional_float(data, "learning_rate", path)
    numeric_momentum = _optional_float(data, "momentum", path)
    numeric_weight_decay = _optional_float(data, "weight_decay", path)
    device = _optional_device(data, path)
    fixture_client_count = _optional_int(data, "fixture_client_count", path)
    fixture_benign_rows = _optional_int(data, "fixture_benign_rows", path)
    fixture_attack_rows = _optional_int(data, "fixture_attack_rows", path)
    fixture_feature_count = _optional_int(data, "fixture_feature_count", path)
    fixture_benign_mean_step = _optional_float(data, "fixture_benign_mean_step", path)
    fixture_attack_mean = _optional_float(data, "fixture_attack_mean", path)
    fixture_feature_std = _optional_float(data, "fixture_feature_std", path)
    full_participation = _require_bool(data, "full_participation", path) if "full_participation" in data else None
    validate_anchor_training_fields(
        status,
        rounds,
        local_epochs,
        numeric_learning_rate,
        numeric_momentum,
        numeric_weight_decay,
        device,
        fixture_client_count,
        fixture_benign_rows,
        fixture_attack_rows,
        fixture_feature_count,
        fixture_benign_mean_step,
        fixture_attack_mean,
        fixture_feature_std,
        full_participation,
    )
    return TrainingConfig(
        name=data["name"],
        status=status,
        dataset_id=dataset_id,
        training_algorithm=training_algorithm,
        seed_plan=seed_plan,
        rounds=rounds,
        local_epochs=local_epochs,
        learning_rate=numeric_learning_rate,
        momentum=numeric_momentum,
        weight_decay=numeric_weight_decay,
        full_participation=full_participation,
        device=device,
        fixture_client_count=fixture_client_count,
        fixture_benign_rows=fixture_benign_rows,
        fixture_attack_rows=fixture_attack_rows,
        fixture_feature_count=fixture_feature_count,
        fixture_benign_mean_step=fixture_benign_mean_step,
        fixture_attack_mean=fixture_attack_mean,
        fixture_feature_std=fixture_feature_std,
    )


def load_thresholding_config(path: Path) -> ThresholdingConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _schema_fields(ThresholdingConfig), path)
    try:
        status = ConfigStatus(data["status"])
        policies = tuple(_parse_policy(p, path) for p in data["policies"])
        q_values = tuple(float(q) for q in data["q_values"])
        calibration_label_scope = CalibrationLabelScope(data["calibration_label_scope"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    has_family_taxonomy = _require_bool(data, "has_family_taxonomy", path) if "has_family_taxonomy" in data else None
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
    _reject_unknown_fields(data, _schema_fields(AnalysisConfig), path)
    try:
        status = ConfigStatus(data["status"])
        analysis_kind = AnalysisKind(data["analysis_kind"])
    except (KeyError, ValueError) as exc:
        raise ConfigLoadError(f"{path}: {exc}") from exc
    return AnalysisConfig(name=data["name"], status=status, analysis_kind=analysis_kind)


def load_suite_config(path: Path) -> SuiteConfig:
    data = load_yaml_document(path)
    _reject_unknown_fields(data, _schema_fields(SuiteConfig), path)
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
    mini_seed_count = _optional_int(data, "mini_seed_count", path)
    expected_client_count = _optional_int(data, "expected_client_count", path)
    raw_layout = data.get("artifact_layout")
    if raw_layout is not None and not isinstance(raw_layout, Mapping):
        raise ConfigLoadError(f"{path}: artifact_layout must be a YAML mapping when present")
    artifact_layout = None
    if raw_layout is not None:
        _reject_unknown_fields(raw_layout, _schema_fields(AnchorArtifactLayout), path)
        try:
            artifact_layout = AnchorArtifactLayout(**raw_layout)
        except TypeError as exc:
            raise ConfigLoadError(f"{path}: invalid artifact_layout: {exc}") from exc

    return SuiteConfig(
        name=data["name"],
        status=status,
        regimes=regimes,
        experiment_ids=experiment_ids,
        training_enabled=training_enabled,
        requires_score_reuse=requires_score_reuse,
        allow_training_override=allow_training_override,
        dataset_config=data.get("dataset_config"),
        training_config=data.get("training_config"),
        model_config=data.get("model_config"),
        thresholding_config=data.get("thresholding_config"),
        mini_seed_count=mini_seed_count,
        expected_client_count=expected_client_count,
        artifact_layout=artifact_layout,
    )
