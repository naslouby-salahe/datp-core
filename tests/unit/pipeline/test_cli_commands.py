"""CLI correctness: truthful validate output, exit codes, structured JSON drift output, and
no full-application construction for configuration-only commands."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from datp_core import cli as cli_app_module
from datp_core.cli import app

runner = CliRunner()


def _copy_real_config_tree(tmp_path: Path) -> Path:
    for name in ("runtime.yaml", "protocols.yaml", "experiments.yaml"):
        shutil.copy(f"configs/{name}", tmp_path / name)
    (tmp_path / "datasets").mkdir()
    for source in Path("configs/datasets").glob("*.yaml"):
        shutil.copy(source, tmp_path / "datasets" / source.name)
    return tmp_path


def test_config_validate_succeeds_on_the_real_configuration() -> None:
    result = runner.invoke(app, ["config", "validate"])
    assert result.exit_code == 0
    assert "strictly validated successfully" in result.stdout


def test_config_validate_fails_truthfully_on_an_invalid_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_dir = _copy_real_config_tree(tmp_path)

    with open(config_dir / "experiments.yaml") as handle:
        experiments = yaml.safe_load(handle)
    experiments["experiments"][0] = {
        **experiments["experiments"][0],
        "training_profile": "an_unregistered_training_profile",
    }
    (config_dir / "experiments.yaml").write_text(yaml.safe_dump(experiments, sort_keys=False))

    monkeypatch.setenv("DATP_CONFIG_ROOT", str(config_dir))
    result = runner.invoke(app, ["config", "validate"])

    assert result.exit_code == 1
    assert "Configuration validation failed" in result.stdout
    assert "an_unregistered_training_profile" in result.stdout


def test_config_explain_drift_prints_structured_json_and_exits_zero_when_no_drift(tmp_path: Path) -> None:
    same_file = tmp_path / "protocols_copy.yaml"
    shutil.copy("configs/protocols.yaml", same_file)

    result = runner.invoke(app, ["config", "explain-drift", str(same_file), "configs/protocols.yaml"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["has_drift"] is False
    assert payload["diff_entries"] == []


def test_config_explain_drift_reports_drift_and_exits_nonzero() -> None:
    result = runner.invoke(app, ["config", "explain-drift", "configs/protocols.yaml", "configs/runtime.yaml"])

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["has_drift"] is True
    assert len(payload["diff_entries"]) > 0


def test_config_fingerprint_prints_both_fingerprints() -> None:
    result = runner.invoke(app, ["config", "fingerprint"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["scientific_fingerprint"]) == 64
    assert len(payload["execution_fingerprint"]) == 64


def test_catalogue_describe_never_constructs_the_full_application(monkeypatch: pytest.MonkeyPatch) -> None:
    def _fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("catalogue describe must not build the full application graph")

    monkeypatch.setattr(cli_app_module, "build_application", _fail_if_called)

    result = runner.invoke(app, ["catalogue", "describe"])

    assert result.exit_code == 0
    assert "Catalogue Summary" in result.stdout
