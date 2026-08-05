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


def test_protocol_validation_is_exposed_without_scientific_overrides() -> None:
    result = runner.invoke(app, ["plan", "validate-protocols"])
    assert result.exit_code == 0
    output = _plain(result.stdout)
    assert "populations=" in output
    assert "experiments=" in output
    assert "suppressed=" in output


def test_declared_experiment_and_population_are_inspectable_by_enum_identity() -> None:
    experiment = runner.invoke(app, ["inspect", "experiment", "shared_vs_local_confirmation"])
    population = runner.invoke(app, ["inspect", "population", "nbaiot_natural_devices"])
    assert experiment.exit_code == 0
    assert "role=confirmatory" in _plain(experiment.stdout)
    assert population.exit_code == 0
    assert "identity=physical_devices" in _plain(population.stdout)


def test_inspection_rejects_undeclared_scientific_identity() -> None:
    result = runner.invoke(app, ["inspect", "experiment", "invented_experiment"])
    assert result.exit_code != 0


def test_confirmatory_seed_rejects_arbitrary_scientific_override() -> None:
    result = runner.invoke(app, ["run", "confirmatory-seed", "--training-seed", "999"])
    assert result.exit_code != 0
    assert "declared confirmatory seeds" in _plain(result.output)


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
