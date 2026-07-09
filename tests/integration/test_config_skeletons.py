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

# No Phase 1 config skeleton may reach a runnable readiness level: there is no
# suite runner, dataset loader, training loop, or thresholding implementation yet.
_MAX_PHASE1_STATUS = {ConfigStatus.CONTRACT_ONLY, ConfigStatus.IMPLEMENTATION_PENDING}


def test_all_dataset_configs_parse_and_are_phase1_readiness():
    for path in sorted((CONFIGS / "datasets").glob("*.yaml")):
        config = load_dataset_config(path)
        assert config.status in _MAX_PHASE1_STATUS, path


def test_all_thresholding_configs_parse_and_are_phase1_readiness():
    for path in sorted((CONFIGS / "thresholding").glob("*.yaml")):
        config = load_thresholding_config(path)
        assert config.status in _MAX_PHASE1_STATUS, path


def test_all_analysis_configs_parse_and_are_phase1_readiness():
    for path in sorted((CONFIGS / "analysis").glob("*.yaml")):
        config = load_analysis_config(path)
        assert config.status in _MAX_PHASE1_STATUS, path


def test_all_suite_configs_parse_and_are_phase1_readiness():
    for path in sorted((CONFIGS / "suites").glob("*.yaml")):
        config = load_suite_config(path)
        assert config.status in _MAX_PHASE1_STATUS, path


def test_all_training_configs_parse_and_are_phase1_readiness():
    path = CONFIGS / "training" / "base_autoencoder.yaml"
    architecture = load_model_architecture_config(path)
    assert architecture.status in _MAX_PHASE1_STATUS

    for path in sorted((CONFIGS / "training").glob("*.yaml")):
        if path.name == "base_autoencoder.yaml":
            continue
        config = load_training_config(path)
        assert config.status in _MAX_PHASE1_STATUS, path


def test_full_journal_suite_refuses_full_execution_during_phase1():
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
