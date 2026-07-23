"""Structured configuration drift: formatting-only changes produce no drift, real scientific
value changes produce named path-level drift entries, execution-only changes never leak into
scientific drift, and additions/removals are reported distinctly."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from datp_core.configuration.project import (
    ExplainAuthoredConfigurationDrift,
    ExplainExecutionConfigurationDrift,
    ExplainResolvedScientificDrift,
)
from datp_core.configuration.project import resolve_project_configuration


def _copy_real_config_tree(tmp_path: Path) -> Path:
    for name in ("runtime.yaml", "protocols.yaml", "experiments.yaml"):
        shutil.copy(f"configs/{name}", tmp_path / name)
    (tmp_path / "datasets").mkdir()
    for source in Path("configs/datasets").glob("*.yaml"):
        shutil.copy(source, tmp_path / "datasets" / source.name)
    return tmp_path


def test_no_drift_between_identical_resolved_configurations() -> None:
    config_a = resolve_project_configuration()
    config_b = resolve_project_configuration()

    report = ExplainResolvedScientificDrift().execute(current_config=config_a, expected_config=config_b)
    assert report.has_drift is False
    assert report.diff_entries == ()


def test_formatting_only_authored_yaml_change_produces_no_drift(tmp_path: Path) -> None:
    with open("configs/protocols.yaml") as handle:
        original = yaml.safe_load(handle)

    reformatted_path = tmp_path / "protocols_reformatted.yaml"
    # Different key order and whitespace, same values -- yaml.safe_dump with sort_keys=True
    # reorders every key relative to the authored file.
    reformatted_path.write_text(yaml.safe_dump(original, sort_keys=True, default_flow_style=False, indent=4))

    report = ExplainAuthoredConfigurationDrift().execute(
        current_yaml_path=reformatted_path,
        expected_yaml_path=Path("configs/protocols.yaml"),
    )
    assert report.has_drift is False
    assert report.diff_entries == ()


def test_real_scientific_value_change_produces_a_named_drift_entry(tmp_path: Path) -> None:
    config_dir = _copy_real_config_tree(tmp_path)
    expected_config = resolve_project_configuration(config_dir=config_dir)

    with open(config_dir / "protocols.yaml") as handle:
        protocols = yaml.safe_load(handle)
    protocols["model_architectures"]["fixed_autoencoder"]["activation"] = "gelu"
    (config_dir / "protocols.yaml").write_text(yaml.safe_dump(protocols, sort_keys=False))

    current_config = resolve_project_configuration(config_dir=config_dir)
    report = ExplainResolvedScientificDrift().execute(current_config=current_config, expected_config=expected_config)

    assert report.has_drift is True
    changed_paths = [entry.path for entry in report.diff_entries]
    assert any("fixed_autoencoder" in path and "activation" in path for path in changed_paths)
    activation_entry = next(entry for entry in report.diff_entries if "activation" in entry.path)
    assert activation_entry.kind == "changed"
    assert activation_entry.old_value == "relu"
    assert activation_entry.new_value == "gelu"


def test_execution_only_change_does_not_produce_scientific_drift(tmp_path: Path) -> None:
    config_dir = _copy_real_config_tree(tmp_path)
    expected_config = resolve_project_configuration(config_dir=config_dir)

    with open(config_dir / "runtime.yaml") as handle:
        runtime = yaml.safe_load(handle)
    runtime["execution_profiles"]["scientific"]["concurrency"]["worker_count"] = 99
    (config_dir / "runtime.yaml").write_text(yaml.safe_dump(runtime, sort_keys=False))

    current_config = resolve_project_configuration(config_dir=config_dir)

    scientific_report = ExplainResolvedScientificDrift().execute(
        current_config=current_config, expected_config=expected_config
    )
    execution_report = ExplainExecutionConfigurationDrift().execute(
        current_config=current_config, expected_config=expected_config
    )

    assert scientific_report.has_drift is False
    assert scientific_report.diff_entries == ()
    assert execution_report.has_drift is True
    assert len(execution_report.diff_entries) > 0


def test_adding_a_sweep_value_is_reported_as_an_addition(tmp_path: Path) -> None:
    config_dir = _copy_real_config_tree(tmp_path)
    expected_config = resolve_project_configuration(config_dir=config_dir)

    with open(config_dir / "experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    for experiment in experiments["experiments"]:
        if experiment["name"] == "threshold_quantile_sensitivity":
            experiment["sweeps"]["threshold_quantile"]["values"].append(0.999)
    (config_dir / "experiments.yaml").write_text(yaml.safe_dump(experiments, sort_keys=False))

    current_config = resolve_project_configuration(config_dir=config_dir)
    report = ExplainResolvedScientificDrift().execute(current_config=current_config, expected_config=expected_config)

    assert report.has_drift is True
    assert any(entry.kind == "added" for entry in report.diff_entries)


def test_removing_a_sweep_value_is_reported_as_a_removal(tmp_path: Path) -> None:
    config_dir = _copy_real_config_tree(tmp_path)
    expected_config = resolve_project_configuration(config_dir=config_dir)

    with open(config_dir / "experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    for experiment in experiments["experiments"]:
        if experiment["name"] == "threshold_quantile_sensitivity":
            experiment["sweeps"]["threshold_quantile"]["values"].pop()
    (config_dir / "experiments.yaml").write_text(yaml.safe_dump(experiments, sort_keys=False))

    current_config = resolve_project_configuration(config_dir=config_dir)
    report = ExplainResolvedScientificDrift().execute(current_config=current_config, expected_config=expected_config)

    assert report.has_drift is True
    assert any(entry.kind == "removed" for entry in report.diff_entries)


@pytest.mark.parametrize("use_case_cls", [ExplainResolvedScientificDrift, ExplainExecutionConfigurationDrift])
def test_no_drift_reports_true_equality_for_resolved_projections(use_case_cls) -> None:
    config = resolve_project_configuration()
    report = use_case_cls().execute(current_config=config, expected_config=config)
    assert report.has_drift is False
    assert report.diff_entries == ()
