import pytest

from datp_core.config.schemas import CalibrationLabelScope
from datp_core.config.validation import (
    ConfigValidationError,
    validate_benign_only_calibration,
    validate_dataset_regime_pair,
    validate_q,
    validate_seed_plan,
    validate_suite_training_flag,
    validate_threshold_policy_scope,
)
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import Comparator, ThresholdPolicy
from datp_core.domain.regimes import Regime


def test_validate_dataset_regime_pair_accepts_known_combination():
    validate_dataset_regime_pair(DatasetId.N_BAIOT, Regime.A)
    validate_dataset_regime_pair(DatasetId.N_BAIOT, Regime.C)


def test_validate_dataset_regime_pair_rejects_unknown_combination():
    with pytest.raises(ConfigValidationError):
        validate_dataset_regime_pair(DatasetId.N_BAIOT, Regime.D)


def test_validate_q_rejects_out_of_range():
    with pytest.raises(ConfigValidationError):
        validate_q(0.0)
    with pytest.raises(ConfigValidationError):
        validate_q(1.0)
    validate_q(0.95)


def test_validate_seed_plan_rejects_duplicates():
    with pytest.raises(ConfigValidationError):
        validate_seed_plan((0, 0, 1))
    validate_seed_plan((0, 1, 2))


def test_validate_threshold_policy_scope_b3_requires_taxonomy():
    with pytest.raises(ConfigValidationError):
        validate_threshold_policy_scope(ThresholdPolicy.B3, has_family_taxonomy=False, cluster_k=None)
    validate_threshold_policy_scope(ThresholdPolicy.B3, has_family_taxonomy=True, cluster_k=None)


def test_validate_threshold_policy_scope_b4_requires_positive_k():
    with pytest.raises(ConfigValidationError):
        validate_threshold_policy_scope(ThresholdPolicy.B4, has_family_taxonomy=False, cluster_k=None)
    with pytest.raises(ConfigValidationError):
        validate_threshold_policy_scope(ThresholdPolicy.B4, has_family_taxonomy=False, cluster_k=0)
    validate_threshold_policy_scope(ThresholdPolicy.B4, has_family_taxonomy=False, cluster_k=3)


def test_validate_benign_only_calibration_accepts_only_typed_benign_scope():
    with pytest.raises(ValueError):
        CalibrationLabelScope("benign_and_attack")
    validate_benign_only_calibration(
        Comparator.B_FEDSTATS_BENIGN,
        CalibrationLabelScope.BENIGN_ONLY,
    )


def test_validate_suite_training_flag_blocks_threshold_only_training():
    with pytest.raises(ConfigValidationError):
        validate_suite_training_flag(training_enabled=True, requires_score_reuse=True, allow_training_override=False)
    validate_suite_training_flag(training_enabled=True, requires_score_reuse=True, allow_training_override=True)
    validate_suite_training_flag(training_enabled=False, requires_score_reuse=True, allow_training_override=False)
