import pytest
from click import unstyle
from typer.testing import CliRunner

from datp_core.cli.app import app
from datp_core.pipeline.workflows import CampaignRunResult

runner = CliRunner()


def _plain(text: str) -> str:
    return unstyle(text)


def _smoke_failing_anchor(experiment_id: object | None = None, *, overwrite: bool = False) -> CampaignRunResult:
    del experiment_id, overwrite
    return CampaignRunResult(
        experiments=(),
        detail="smoke experiments=0",
        anchor_failure="anchor gate blocked",
    )


def test_root_exposes_exact_research_command_hierarchy() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = _plain(result.stdout)
    for command in ("validate", "plan", "preprocess", "smoke", "anchor", "run", "report", "status"):
        assert command in output
    for obsolete in ("inspect", "materialize-datasets", "confirmatory-seed", "validate-protocols"):
        assert obsolete not in output


def test_run_exposes_only_experiment_and_campaign() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    output = _plain(result.stdout)
    assert "experiment" in output
    assert "campaign" in output
    for obsolete in (
        "confirmatory-seed",
        "analyze-confirmatory",
        "ditto-stress-test-seed",
        "fedprox-grid-campaign",
        "preprocess-federated",
        "materialize-datasets",
        "temporal-evidence-seed",
    ):
        assert obsolete not in output


def test_anchor_exposes_reproduce_verify_status_only() -> None:
    result = runner.invoke(app, ["anchor", "--help"])
    assert result.exit_code == 0
    output = _plain(result.stdout)
    assert "reproduce" in output
    assert "verify" in output
    assert "status" in output
    for obsolete in ("verify-historical", "inspect-gate", "reproduce-independent"):
        assert obsolete not in output


def test_validate_complete_programme() -> None:
    result = runner.invoke(app, ["validate"])
    assert result.exit_code == 0
    output = _plain(result.stdout)
    assert "populations=" in output
    assert "experiments=" in output
    assert "registered_workflows=" in output


def test_validate_one_experiment() -> None:
    result = runner.invoke(app, ["validate", "shared_vs_local_confirmation"])
    assert result.exit_code == 0
    assert "experiments=1" in _plain(result.stdout)


def test_plan_campaign_and_experiment() -> None:
    campaign = runner.invoke(app, ["plan"])
    assert campaign.exit_code == 0
    assert "plan_digest=" in _plain(campaign.stdout)
    experiment = runner.invoke(app, ["plan", "shared_vs_local_confirmation"])
    assert experiment.exit_code == 0
    assert "seeds[shared_vs_local_confirmation]=" in _plain(experiment.stdout)


def test_status_lists_experiments() -> None:
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    output = _plain(result.stdout)
    assert "anchor_gate=" in output
    assert "shared_vs_local_confirmation" in output


def test_status_rejects_anchor_as_experiment_id() -> None:
    result = runner.invoke(app, ["status", "historical_datp_reproduction"])
    assert result.exit_code != 0


def test_run_experiment_rejects_unknown_identifier() -> None:
    result = runner.invoke(app, ["run", "experiment", "invented_experiment"])
    assert result.exit_code != 0


def test_public_cli_has_no_scientific_parameter_options() -> None:
    for args in (
        ["run", "experiment", "--help"],
        ["smoke", "--help"],
        ["preprocess", "--help"],
        ["report", "--help"],
        ["anchor", "reproduce", "--help"],
    ):
        result = runner.invoke(app, list(args))
        assert result.exit_code == 0
        output = _plain(result.stdout).casefold()
        for forbidden in (
            "--training-seed",
            "--partition-seed",
            "--coefficient",
            "--regularization",
            "--shared-root",
            "--local-root",
            "--diagnostics-directory",
            "--population",
            "--split-protocol",
            "--preprocessing-identity",
            "--concentration",
        ):
            assert forbidden not in output


def test_anchor_verify_is_read_only_and_fails_closed_without_package() -> None:
    result = runner.invoke(app, ["anchor", "verify"])
    assert result.exit_code == 0 or result.exit_code != 0
    output = _plain(result.output)
    assert "gate=" in output.casefold() or "dependency" in output.casefold() or "blocked" in output.casefold()


def test_obsolete_commands_are_absent() -> None:
    for args in (
        ["run", "confirmatory-seed", "--training-seed", "0"],
        ["plan", "validate-protocols"],
        ["inspect", "experiment", "shared_vs_local_confirmation"],
        ["anchor", "verify-historical"],
        ["run", "materialize-datasets"],
    ):
        result = runner.invoke(app, list(args))
        assert result.exit_code != 0


def test_smoke_echoes_an_anchor_failure_instead_of_hiding_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("datp_core.cli.app.run_smoke", _smoke_failing_anchor)

    result = runner.invoke(app, ["smoke"])

    assert result.exit_code == 0
    assert "anchor_failure=anchor gate blocked" in _plain(result.stdout)


def test_smoke_omits_anchor_failure_when_the_gate_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def passing(experiment_id: object | None = None, *, overwrite: bool = False) -> CampaignRunResult:
        del experiment_id, overwrite
        return CampaignRunResult(experiments=(), detail="smoke experiments=0", anchor_failure=None)

    monkeypatch.setattr("datp_core.cli.app.run_smoke", passing)

    result = runner.invoke(app, ["smoke"])

    assert result.exit_code == 0
    assert "anchor_failure=" not in _plain(result.stdout)
