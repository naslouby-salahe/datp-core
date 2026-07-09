from pathlib import Path

from datp_core.config.loader import (
    load_analysis_config,
    load_dataset_config,
    load_model_architecture_config,
    load_suite_config,
    load_thresholding_config,
    load_training_config,
)
from datp_core.config.schemas import ConfigStatus
from datp_core.utils.paths import find_repo_root

REPO_ROOT = find_repo_root(Path(__file__))
CONFIGS = REPO_ROOT / "configs"

# Phase 2 promotes only the N-BaIoT anchor model and FedAvg configs to smoke readiness.
_CONTRACT_STATUSES = {ConfigStatus.CONTRACT_ONLY, ConfigStatus.IMPLEMENTATION_PENDING}


def test_nbaiot_dataset_config_is_smoke_ready_and_others_remain_contract_only():
    for path in sorted((CONFIGS / "datasets").glob("*.yaml")):
        config = load_dataset_config(path)
        expected_status = ConfigStatus.READY_FOR_SMOKE if path.name == "nbaiot.yaml" else ConfigStatus.CONTRACT_ONLY
        assert config.status is expected_status, path


def test_anchor_thresholding_config_is_smoke_ready_and_others_remain_contract_only():
    for path in sorted((CONFIGS / "thresholding").glob("*.yaml")):
        config = load_thresholding_config(path)
        expected_status = (
            ConfigStatus.READY_FOR_SMOKE if path.name == "anchor_b1_b2.yaml" else ConfigStatus.CONTRACT_ONLY
        )
        assert config.status is expected_status, path


def test_all_analysis_configs_remain_contract_only():
    for path in sorted((CONFIGS / "analysis").glob("*.yaml")):
        config = load_analysis_config(path)
        assert config.status in _CONTRACT_STATUSES, path


def test_anchor_suite_is_smoke_ready_and_others_remain_contract_only():
    for path in sorted((CONFIGS / "suites").glob("*.yaml")):
        config = load_suite_config(path)
        expected_status = (
            ConfigStatus.READY_FOR_SMOKE if path.name == "confirmatory_regime_a.yaml" else ConfigStatus.CONTRACT_ONLY
        )
        assert config.status is expected_status, path


def test_anchor_training_configs_are_smoke_ready_and_others_remain_contract_only():
    path = CONFIGS / "training" / "base_autoencoder.yaml"
    architecture = load_model_architecture_config(path)
    assert architecture.status is ConfigStatus.READY_FOR_SMOKE

    for path in sorted((CONFIGS / "training").glob("*.yaml")):
        if path.name == "base_autoencoder.yaml":
            continue
        config = load_training_config(path)
        expected_status = (
            ConfigStatus.READY_FOR_SMOKE if path.name == "fedavg_nbaiot.yaml" else ConfigStatus.CONTRACT_ONLY
        )
        assert config.status is expected_status, path


def test_full_journal_suite_refuses_automatic_full_execution():
    config = load_suite_config(CONFIGS / "suites" / "full_journal.yaml")
    assert config.is_runnable is False
    assert config.status is ConfigStatus.CONTRACT_ONLY


def test_confirmatory_suite_recognized_but_not_runnable():
    config = load_suite_config(CONFIGS / "suites" / "confirmatory_regime_a.yaml")
    assert config.name == "confirmatory_regime_a"
    assert config.is_runnable is False


def test_threshold_only_suites_declare_score_reuse_requirement():
    threshold_variants = load_suite_config(CONFIGS / "suites" / "threshold_variants.yaml")
    assert threshold_variants.requires_score_reuse is True
    assert threshold_variants.training_enabled is False

    temporal = load_suite_config(CONFIGS / "suites" / "temporal_recalibration.yaml")
    assert temporal.requires_score_reuse is True
    assert temporal.training_enabled is False
