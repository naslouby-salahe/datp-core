from click import unstyle
from typer.testing import CliRunner

from datp_core.cli.app import app

runner = CliRunner()


def _plain(text: str) -> str:
    return unstyle(text)


def test_root_exposes_thin_command_groups() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = _plain(result.stdout)
    assert "plan" in output
    assert "run" in output
    assert "inspect" in output
    assert "anchor" in output


def test_federated_preprocessing_rejects_centralized_identity() -> None:
    result = runner.invoke(
        app,
        [
            "run",
            "preprocess-federated",
            "--population",
            "nbaiot_natural_devices",
            "--partition-seed",
            "0",
            "--split-protocol",
            "non_temporal_equal_thirds",
            "--preprocessing-identity",
            "centralized_pooled_min_max",
        ],
    )
    assert result.exit_code != 0
    assert "federated_client_local_standard" in _plain(result.output)
