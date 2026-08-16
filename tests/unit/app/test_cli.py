from typer.testing import CliRunner

from datp_core.app.cli.app import app

RUNNER = CliRunner()


def test_root_help_exposes_research_commands() -> None:
    result = RUNNER.invoke(app, ["--help"])
    assert result.exit_code == 0
    for command in ("validate", "plan", "preprocess", "smoke", "anchor", "run", "report", "status", "results"):
        assert command in result.stdout


def test_run_help_exposes_only_experiment_and_campaign() -> None:
    result = RUNNER.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "experiment" in result.stdout
    assert "campaign" in result.stdout


def test_anchor_help_exposes_reproduce_verify_and_status() -> None:
    result = RUNNER.invoke(app, ["anchor", "--help"])
    assert result.exit_code == 0
    assert "reproduce" in result.stdout
    assert "verify" in result.stdout
    assert "status" in result.stdout


def test_preprocess_requires_a_dataset_identifier() -> None:
    result = RUNNER.invoke(app, ["preprocess"])
    assert result.exit_code != 0
