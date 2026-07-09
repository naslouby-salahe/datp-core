"""Config validation rules that enforce protocol identity, not just field types."""

from __future__ import annotations

from datp_core.domain.clients import ClientIdentityType
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import Comparator, ThresholdPolicy
from datp_core.domain.regimes import Regime
from datp_core.domain.seeds import SeedPlan, SeedPlanError, SeedRole

from .schemas import DATASET_REGIME_COMPATIBILITY, CalibrationLabelScope, ConfigStatus

_STATUSES_REQUIRING_CLIENT_IDENTITY = (ConfigStatus.READY_FOR_SMOKE, ConfigStatus.READY_FOR_FULL_RUN)


class ConfigError(ValueError):
    """Base class for config loading/validation failures."""


class ConfigLoadError(ConfigError):
    """A config document is structurally invalid (unknown field, unparsable value)."""


class ConfigValidationError(ConfigError):
    """A config document is structurally valid but violates a protocol rule."""


def validate_dataset_regime_pair(dataset_id: DatasetId, regime: Regime) -> None:
    allowed = DATASET_REGIME_COMPATIBILITY[dataset_id]
    if regime not in allowed:
        raise ConfigValidationError(
            f"{dataset_id} does not support {regime}; allowed regimes: {allowed}"
        )


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


def validate_threshold_policy_scope(
    policy: ThresholdPolicy | Comparator,
    has_family_taxonomy: bool | None,
    cluster_k: int | None,
) -> None:
    if policy is ThresholdPolicy.B3 and has_family_taxonomy is None:
        raise ConfigValidationError("B3 requires an explicit has_family_taxonomy field")
    if policy is ThresholdPolicy.B3 and not has_family_taxonomy:
        raise ConfigValidationError("B3 requires a device-taxonomy family assignment")
    if policy is ThresholdPolicy.B4:
        if cluster_k is None or cluster_k <= 0:
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
