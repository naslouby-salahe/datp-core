"""Config validation rules that enforce protocol identity, not just field types."""

from __future__ import annotations

from datp_core.domain.clients import ClientIdentityType
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import Comparator, ThresholdPolicy
from datp_core.domain.regimes import Regime
from datp_core.domain.seeds import SeedPlan, SeedPlanError, SeedRole
from datp_core.utils.hardware import DeviceType

from .schemas import DATASET_REGIME_COMPATIBILITIES, CalibrationLabelScope, ConfigStatus

_STATUSES_REQUIRING_CLIENT_IDENTITY = (ConfigStatus.READY_FOR_SMOKE, ConfigStatus.READY_FOR_FULL_RUN)


class ConfigError(ValueError):
    """Base class for config loading/validation failures."""


class ConfigLoadError(ConfigError):
    """A config document is structurally invalid (unknown field, unparsable value)."""


class ConfigValidationError(ConfigError):
    """A config document is structurally valid but violates a protocol rule."""


def validate_dataset_regime_pair(dataset_id: DatasetId, regime: Regime) -> None:
    for compatibility in DATASET_REGIME_COMPATIBILITIES:
        if compatibility.dataset_id is dataset_id:
            if regime not in compatibility.regimes:
                raise ConfigValidationError(
                    f"{dataset_id} does not support {regime}; allowed regimes: {compatibility.regimes}"
                )
            return
    raise ConfigValidationError(f"missing dataset-regime compatibility for {dataset_id}")


def validate_client_identity_presence(
    status: ConfigStatus,
    client_identity_type: ClientIdentityType | None,
) -> None:
    """Client identity may stay undecided (e.g. Edge-IIoTset pending P6-T02) below smoke readiness.

    A rejected regime (e.g. CICIoT2023 B-b) never needs one: its status never
    advances past contract_only, so it never trips this check.
    """
    if client_identity_type is None and status in _STATUSES_REQUIRING_CLIENT_IDENTITY:
        raise ConfigValidationError(f"client_identity_type is required once status reaches {status}")


def validate_q(q: float) -> None:
    if not (0.0 < q < 1.0):
        raise ConfigValidationError(f"q must be strictly between 0 and 1, got {q}")


def validate_q_values(q_values: tuple[float, ...]) -> None:
    if not q_values:
        raise ConfigValidationError("q_values must not be empty")
    for q in q_values:
        validate_q(q)


def validate_policies_nonempty(policies: tuple[ThresholdPolicy | Comparator, ...]) -> None:
    if not policies:
        raise ConfigValidationError("policies must not be empty")


def validate_seed_plan(seeds: tuple[int, ...]) -> None:
    try:
        SeedPlan(seeds=seeds, role=SeedRole.ANALYSIS)
    except SeedPlanError as exc:
        raise ConfigValidationError(str(exc)) from exc


def validate_anchor_training_fields(
    status: ConfigStatus,
    rounds: int | None,
    local_epochs: int | None,
    learning_rate: float | None,
    momentum: float | None,
    weight_decay: float | None,
    device: DeviceType | None,
    fixture_client_count: int | None,
    fixture_benign_rows: int | None,
    fixture_attack_rows: int | None,
    fixture_feature_count: int | None,
    fixture_benign_mean_step: float | None,
    fixture_attack_mean: float | None,
    fixture_feature_std: float | None,
    full_participation: bool | None,
) -> None:
    if status not in _STATUSES_REQUIRING_CLIENT_IDENTITY:
        return
    if (
        rounds is None
        or local_epochs is None
        or learning_rate is None
        or momentum is None
        or weight_decay is None
        or device is None
        or fixture_client_count is None
        or fixture_benign_rows is None
        or fixture_attack_rows is None
        or fixture_feature_count is None
        or fixture_benign_mean_step is None
        or fixture_attack_mean is None
        or fixture_feature_std is None
        or full_participation is None
    ):
        raise ConfigValidationError("smoke-ready training config requires every anchor runtime field")
    if rounds < 1 or local_epochs != 1 or learning_rate <= 0.0:
        raise ConfigValidationError(
            "anchor training requires rounds >= 1, local_epochs == 1, and positive learning_rate"
        )
    if momentum < 0.0 or weight_decay < 0.0:
        raise ConfigValidationError("anchor optimizer settings must be non-negative")
    if not full_participation:
        raise ConfigValidationError("anchor FedAvg requires full_participation=true")
    if device is not DeviceType.CUDA:
        raise ConfigValidationError("anchor experiments require the configured CUDA device")
    if fixture_client_count < 2 or fixture_benign_rows < 500 or fixture_attack_rows < 1 or fixture_feature_count < 1:
        raise ConfigValidationError("fixture dimensions must support paired metrics and calibration eligibility")
    if fixture_benign_mean_step <= 0.0 or fixture_attack_mean <= 0.0 or fixture_feature_std <= 0.0:
        raise ConfigValidationError("fixture distribution parameters must be positive")


def validate_anchor_architecture_fields(status: ConfigStatus, hidden_dim: int | None) -> None:
    if status in _STATUSES_REQUIRING_CLIENT_IDENTITY and (hidden_dim is None or hidden_dim < 1):
        raise ConfigValidationError("smoke-ready autoencoder config requires a positive hidden_dim")


def validate_anchor_split_fields(
    status: ConfigStatus,
    train_fraction: float | None,
    calibration_fraction: float | None,
) -> None:
    if status not in _STATUSES_REQUIRING_CLIENT_IDENTITY:
        return
    if train_fraction is None or calibration_fraction is None:
        raise ConfigValidationError("smoke-ready dataset config requires train_fraction and calibration_fraction")
    if not 0.0 < train_fraction < 1.0 or not 0.0 < calibration_fraction < 1.0:
        raise ConfigValidationError("split fractions must be strictly between zero and one")
    if train_fraction + calibration_fraction >= 1.0:
        raise ConfigValidationError("split fractions must leave held-out benign test data")


def validate_threshold_policy_scope(
    policy: ThresholdPolicy | Comparator,
    has_family_taxonomy: bool | None,
    cluster_k: int | None,
) -> None:
    if policy is ThresholdPolicy.B3 and has_family_taxonomy is None:
        raise ConfigValidationError("B3 requires an explicit has_family_taxonomy field")
    if policy is ThresholdPolicy.B3 and not has_family_taxonomy:
        raise ConfigValidationError("B3 requires a device-taxonomy family assignment")
    if policy is ThresholdPolicy.B4 and (cluster_k is None or cluster_k <= 0):
        raise ConfigValidationError(f"B4 requires a positive cluster K, got {cluster_k}")


def validate_benign_only_calibration(
    policy: ThresholdPolicy | Comparator,
    calibration_label_scope: CalibrationLabelScope,
) -> None:
    if policy is Comparator.B_FEDSTATS_BENIGN and calibration_label_scope is not CalibrationLabelScope.BENIGN_ONLY:
        raise ConfigValidationError(
            "B-FedStatsBenign calibration must be benign_only; "
            f"got calibration_label_scope={calibration_label_scope.value!r}"
        )


def validate_suite_training_flag(
    training_enabled: bool,
    requires_score_reuse: bool,
    allow_training_override: bool,
) -> None:
    if requires_score_reuse and training_enabled and not allow_training_override:
        raise ConfigValidationError(
            "a threshold-only suite (requires_score_reuse=True) must not enable training "
            "unless allow_training_override is explicitly set"
        )
