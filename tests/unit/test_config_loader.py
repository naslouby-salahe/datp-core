import pytest
import yaml

from datp_core.config.loader import (
    load_analysis_config,
    load_dataset_config,
    load_model_architecture_config,
    load_suite_config,
    load_thresholding_config,
    load_training_config,
)
from datp_core.config.schemas import (
    AnalysisKind,
    ArchitectureFamily,
    CalibrationLabelScope,
    ConfigStatus,
)
from datp_core.config.validation import ConfigError, ConfigLoadError
from datp_core.domain.datasets import DatasetId
from datp_core.domain.policies import Comparator, ThresholdPolicy
from datp_core.domain.regimes import Regime


def _write(tmp_path, name, data):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data))
    return path


def test_valid_minimal_dataset_config_loads(tmp_path):
    path = _write(
        tmp_path,
        "nbaiot.yaml",
        {
            "name": "nbaiot",
            "status": "contract_only",
            "dataset_id": "nbaiot",
            "regimes": ["A", "C"],
            "client_identity_type": "physical_device",
            "raw_subdirectory": "nbaiot",
        },
    )
    config = load_dataset_config(path)
    assert config.dataset_id is DatasetId.N_BAIOT
    assert config.regimes == (Regime.A, Regime.C)
    assert config.status is ConfigStatus.CONTRACT_ONLY


def test_rejected_regime_dataset_config_loads_without_client_identity_type(tmp_path):
    path = _write(
        tmp_path,
        "ciciot2023_rejected_b_b.yaml",
        {
            "name": "ciciot2023_rejected_b_b",
            "status": "contract_only",
            "dataset_id": "ciciot2023",
            "regimes": ["B_B_REJECTED_NO_METADATA"],
            "raw_subdirectory": "ciciot2023",
        },
    )
    config = load_dataset_config(path)
    assert config.client_identity_type is None


def test_smoke_ready_dataset_config_requires_client_identity_type(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "ciciot2023_file_level",
            "status": "ready_for_smoke",
            "dataset_id": "ciciot2023",
            "regimes": ["B_A"],
            "raw_subdirectory": "ciciot2023",
        },
    )
    with pytest.raises(ConfigError):
        load_dataset_config(path)


def test_unknown_field_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "nbaiot",
            "status": "contract_only",
            "dataset_id": "nbaiot",
            "regimes": ["A"],
            "client_identity_type": "physical_device",
            "raw_subdirectory": "nbaiot",
            "totally_unexpected_field": True,
        },
    )
    with pytest.raises(ConfigLoadError):
        load_dataset_config(path)


def test_invalid_regime_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "nbaiot",
            "status": "contract_only",
            "dataset_id": "nbaiot",
            "regimes": ["Z_NOT_A_REGIME"],
            "client_identity_type": "physical_device",
            "raw_subdirectory": "nbaiot",
        },
    )
    with pytest.raises(ConfigLoadError):
        load_dataset_config(path)


def test_invalid_dataset_regime_pair_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "nbaiot",
            "status": "contract_only",
            "dataset_id": "nbaiot",
            "regimes": ["D"],
            "client_identity_type": "physical_device",
            "raw_subdirectory": "nbaiot",
        },
    )
    with pytest.raises(ConfigError):
        load_dataset_config(path)


def test_invalid_seed_plan_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "fedavg_nbaiot",
            "status": "contract_only",
            "dataset_id": "nbaiot",
            "training_algorithm": "fedavg",
            "seed_plan": [0, 0, 1],
        },
    )
    with pytest.raises(ConfigError):
        load_training_config(path)


def test_valid_minimal_model_architecture_config_loads(tmp_path):
    path = _write(
        tmp_path,
        "base_autoencoder.yaml",
        {"name": "base_autoencoder", "status": "contract_only", "architecture_family": "autoencoder"},
    )
    config = load_model_architecture_config(path)
    assert config.architecture_family is ArchitectureFamily.AUTOENCODER


def test_valid_minimal_training_config_loads(tmp_path):
    path = _write(
        tmp_path,
        "fedavg_nbaiot.yaml",
        {
            "name": "fedavg_nbaiot",
            "status": "contract_only",
            "dataset_id": "nbaiot",
            "training_algorithm": "fedavg",
            "seed_plan": [0, 1, 2],
        },
    )
    config = load_training_config(path)
    assert config.seed_plan == (0, 1, 2)


def test_invalid_policy_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {"name": "x", "status": "contract_only", "policies": ["B5"], "q_values": [0.95]},
    )
    with pytest.raises(ConfigLoadError):
        load_thresholding_config(path)


def test_invalid_q_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "x",
            "status": "contract_only",
            "policies": ["B1"],
            "q_values": [1.5],
            "calibration_label_scope": "benign_only",
        },
    )
    with pytest.raises(ConfigError):
        load_thresholding_config(path)


def test_b3_without_taxonomy_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "x",
            "status": "contract_only",
            "policies": ["B3"],
            "q_values": [0.95],
            "calibration_label_scope": "benign_only",
        },
    )
    with pytest.raises(ConfigError):
        load_thresholding_config(path)


def test_b3_with_taxonomy_loads(tmp_path):
    path = _write(
        tmp_path,
        "ok.yaml",
        {
            "name": "x",
            "status": "contract_only",
            "policies": ["B3"],
            "q_values": [0.95],
            "has_family_taxonomy": True,
            "calibration_label_scope": "benign_only",
        },
    )
    config = load_thresholding_config(path)
    assert config.policies == (ThresholdPolicy.B3,)


def test_b4_invalid_k_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "x",
            "status": "contract_only",
            "policies": ["B4"],
            "q_values": [0.95],
            "cluster_k": 0,
            "calibration_label_scope": "benign_only",
        },
    )
    with pytest.raises(ConfigError):
        load_thresholding_config(path)


def test_b4_valid_k_loads(tmp_path):
    path = _write(
        tmp_path,
        "ok.yaml",
        {
            "name": "x",
            "status": "contract_only",
            "policies": ["B4"],
            "q_values": [0.95],
            "cluster_k": 3,
            "calibration_label_scope": "benign_only",
        },
    )
    config = load_thresholding_config(path)
    assert config.cluster_k == 3


def test_b_fedstats_benign_under_anomaly_labeled_calibration_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "x",
            "status": "contract_only",
            "policies": ["b_fedstats_benign"],
            "q_values": [0.95],
            "calibration_label_scope": "benign_and_attack",
        },
    )
    with pytest.raises(ConfigError):
        load_thresholding_config(path)


def test_b_fedstats_benign_under_benign_only_calibration_loads(tmp_path):
    path = _write(
        tmp_path,
        "ok.yaml",
        {
            "name": "x",
            "status": "contract_only",
            "policies": ["b_fedstats_benign"],
            "q_values": [0.95],
            "calibration_label_scope": "benign_only",
        },
    )
    config = load_thresholding_config(path)
    assert config.policies == (Comparator.B_FEDSTATS_BENIGN,)
    assert config.calibration_label_scope is CalibrationLabelScope.BENIGN_ONLY


def test_thresholding_config_requires_explicit_calibration_label_scope(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {"name": "x", "status": "contract_only", "policies": ["B1"], "q_values": [0.95]},
    )
    with pytest.raises(ConfigLoadError):
        load_thresholding_config(path)


def test_core_ladder_style_multi_policy_config_loads(tmp_path):
    path = _write(
        tmp_path,
        "core_ladder.yaml",
        {
            "name": "core_ladder",
            "status": "contract_only",
            "policies": ["B0", "B1", "B2", "B3", "B4"],
            "q_values": [0.95],
            "has_family_taxonomy": True,
            "cluster_k": 3,
            "calibration_label_scope": "benign_only",
        },
    )
    config = load_thresholding_config(path)
    assert len(config.policies) == 5


def test_quantile_sweep_style_multi_q_config_loads(tmp_path):
    path = _write(
        tmp_path,
        "quantiles.yaml",
        {
            "name": "quantiles",
            "status": "contract_only",
            "policies": ["B1", "B2"],
            "q_values": [0.9, 0.95, 0.975, 0.99],
            "calibration_label_scope": "benign_only",
        },
    )
    config = load_thresholding_config(path)
    assert config.q_values == (0.9, 0.95, 0.975, 0.99)


def test_valid_minimal_analysis_config_loads(tmp_path):
    path = _write(
        tmp_path,
        "statistics.yaml",
        {
            "name": "statistics",
            "status": "contract_only",
            "analysis_kind": "bootstrap_bca_and_paired_tests",
        },
    )
    config = load_analysis_config(path)
    assert config.analysis_kind is AnalysisKind.BOOTSTRAP_BCA_AND_PAIRED_TESTS


def test_threshold_only_suite_with_training_enabled_fails(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "threshold_variants",
            "status": "contract_only",
            "regimes": ["A"],
            "experiment_ids": ["E-V1"],
            "training_enabled": True,
            "requires_score_reuse": True,
            "allow_training_override": False,
        },
    )
    with pytest.raises(ConfigError):
        load_suite_config(path)


def test_threshold_only_suite_with_training_enabled_and_explicit_override_loads(tmp_path):
    path = _write(
        tmp_path,
        "ok.yaml",
        {
            "name": "threshold_variants",
            "status": "contract_only",
            "regimes": ["A"],
            "experiment_ids": ["E-V1"],
            "training_enabled": True,
            "requires_score_reuse": True,
            "allow_training_override": True,
        },
    )
    config = load_suite_config(path)
    assert config.allow_training_override is True


def test_suite_config_requires_explicit_training_override_flag(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "threshold_variants",
            "status": "contract_only",
            "regimes": ["A"],
            "experiment_ids": ["E-V1"],
            "training_enabled": False,
            "requires_score_reuse": True,
        },
    )
    with pytest.raises(ConfigLoadError):
        load_suite_config(path)


def test_suite_config_rejects_string_boolean_fields(tmp_path):
    path = _write(
        tmp_path,
        "bad.yaml",
        {
            "name": "threshold_variants",
            "status": "contract_only",
            "regimes": ["A"],
            "experiment_ids": ["E-V1"],
            "training_enabled": "false",
            "requires_score_reuse": True,
            "allow_training_override": False,
        },
    )
    with pytest.raises(ConfigLoadError):
        load_suite_config(path)


def test_valid_minimal_suite_config_loads(tmp_path):
    path = _write(
        tmp_path,
        "confirmatory_regime_a.yaml",
        {
            "name": "confirmatory_regime_a",
            "status": "contract_only",
            "regimes": ["A"],
            "experiment_ids": ["E-C1"],
            "training_enabled": False,
            "requires_score_reuse": False,
            "allow_training_override": False,
        },
    )
    config = load_suite_config(path)
    assert config.regimes == (Regime.A,)
