from click import unstyle
from typer.testing import CliRunner

from datp_core.cli import app

runner = CliRunner()


def _plain_output(text: str) -> str:
    return unstyle(text)


def test_preprocess_federated_requires_declared_options() -> None:
    result = runner.invoke(app, ["preprocess-federated", "--help"])
    assert result.exit_code == 0
    compact = _plain_output(result.stdout).replace("\n", " ").replace(" ", "")
    assert "--population" in compact
    assert "--partition-seed" in compact
    assert "--split-protocol" in compact
    assert "--preprocessing-iden" in compact


def test_preprocess_federated_rejects_centralized_identity() -> None:
    result = runner.invoke(
        app,
        [
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
    assert "federated_client_local_standard" in _plain_output(result.output)


def test_preprocess_federated_rejects_undeclared_concentration() -> None:
    result = runner.invoke(
        app,
        [
            "preprocess-federated",
            "--population",
            "nbaiot_dirichlet_clients",
            "--partition-seed",
            "0",
            "--split-protocol",
            "non_temporal_equal_thirds",
            "--preprocessing-identity",
            "federated_client_local_standard",
            "--partition-kind",
            "dirichlet",
            "--concentration",
            "0.2",
        ],
    )
    assert result.exit_code != 0
    compact = _plain_output(result.output).replace("\n", " ")
    assert "declared" in compact
    assert "Dirichlet grid" in compact


def test_preprocess_centralized_reference_help() -> None:
    result = runner.invoke(app, ["preprocess-centralized-reference", "--help"])
    assert result.exit_code == 0
    output = _plain_output(result.stdout)
    assert "--population" in output
    assert "centralized" in output.lower()
