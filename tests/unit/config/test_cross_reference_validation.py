"""Cross-document reference validation: the real catalogue passes, and every new reference
check added in the Phase-1 hardening pass reports a dangling reference distinctly."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from datp_core.config.resolver import resolve_project_configuration
from datp_core.config.validation import ProjectConfigurationValidator, validate_all_configurations


def test_the_real_six_document_catalogue_validates_cleanly() -> None:
    report = validate_all_configurations()
    assert report.is_valid
    assert report.errors == ()
    assert report.datasets_checked == 3
    assert report.experiments_checked > 0


def _copy_real_configs_with_experiments_override(tmp_path: Path, experiments: dict) -> Path:
    for name in ("runtime.yaml", "protocols.yaml"):
        shutil.copy(f"configs/{name}", tmp_path / name)
    (tmp_path / "datasets").mkdir()
    for source in Path("configs/datasets").glob("*.yaml"):
        shutil.copy(source, tmp_path / "datasets" / source.name)
    (tmp_path / "experiments.yaml").write_text(yaml.safe_dump(experiments, sort_keys=False))
    return tmp_path


def test_dangling_prerequisite_reference_is_reported(tmp_path: Path) -> None:
    with open("configs/experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    experiments["experiments"][0] = {
        **experiments["experiments"][0],
        "prerequisites": [{"experiment": "does_not_exist_anywhere", "required_outcome": "success"}],
    }
    config_dir = _copy_real_configs_with_experiments_override(tmp_path, experiments)

    resolved = resolve_project_configuration(config_dir=config_dir)
    report = ProjectConfigurationValidator().validate(resolved)

    assert not report.is_valid
    assert any("does_not_exist_anywhere" in error for error in report.errors)


def test_dangling_report_profile_reference_is_reported(tmp_path: Path) -> None:
    with open("configs/experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    experiments["experiments"][0] = {
        **experiments["experiments"][0],
        "reports": ["an_unregistered_report_profile"],
    }
    config_dir = _copy_real_configs_with_experiments_override(tmp_path, experiments)

    resolved = resolve_project_configuration(config_dir=config_dir)
    report = ProjectConfigurationValidator().validate(resolved)

    assert not report.is_valid
    assert any("an_unregistered_report_profile" in error for error in report.errors)


def test_multiple_simultaneous_dangling_references_are_all_reported_together(tmp_path: Path) -> None:
    with open("configs/experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    experiments["experiments"][0] = {
        **experiments["experiments"][0],
        "prerequisites": [{"experiment": "missing_prereq_one", "required_outcome": "success"}],
        "reports": ["missing_report_one"],
    }
    experiments["experiments"][1] = {
        **experiments["experiments"][1],
        "eligibility_policy": "missing_eligibility_policy",
    }
    config_dir = _copy_real_configs_with_experiments_override(tmp_path, experiments)

    resolved = resolve_project_configuration(config_dir=config_dir)
    report = ProjectConfigurationValidator().validate(resolved)

    assert not report.is_valid
    joined = "\n".join(report.errors)
    assert "missing_prereq_one" in joined
    assert "missing_report_one" in joined
    assert "missing_eligibility_policy" in joined
    assert len(report.errors) >= 3


@pytest.mark.parametrize(
    "field_path,dangling_value",
    [
        ("training_profile", "an_unregistered_training_profile"),
        ("checkpoint_profile", "an_unregistered_checkpoint_profile"),
        ("seed_cohort", "an_unregistered_seed_cohort"),
    ],
)
def test_dangling_experiment_level_references_are_reported(
    tmp_path: Path, field_path: str, dangling_value: str
) -> None:
    with open("configs/experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    experiments["experiments"][0] = {**experiments["experiments"][0], field_path: dangling_value}
    config_dir = _copy_real_configs_with_experiments_override(tmp_path, experiments)

    resolved = resolve_project_configuration(config_dir=config_dir)
    report = ProjectConfigurationValidator().validate(resolved)

    assert not report.is_valid
    assert any(dangling_value in error for error in report.errors)
