from json import dumps
from pathlib import Path

from click import unstyle
from typer.testing import CliRunner

from datp_core.cli.app import app
from datp_core.domain.values.counts import Seed
from datp_core.protocols.anchor import HISTORICAL_LOCAL_THRESHOLD_CV_FPR, HISTORICAL_SHARED_THRESHOLD_CV_FPR

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


def test_anchor_verify_rejects_empty_evidence_soft_default() -> None:
    result = runner.invoke(app, ["anchor", "verify"])
    assert result.exit_code != 0
    assert "shared-root" in _plain(result.output).casefold() or "independent" in _plain(result.output).casefold()


def test_anchor_verify_historical_pass_path(tmp_path: Path) -> None:
    shared_root, local_root = _historical_fixture_roots(tmp_path)
    diagnostics = tmp_path / "diag"
    result = runner.invoke(
        app,
        [
            "anchor",
            "verify-historical",
            "--shared-root",
            str(shared_root),
            "--local-root",
            str(local_root),
            "--diagnostics-directory",
            str(diagnostics),
        ],
    )
    assert result.exit_code == 0
    assert "gate=pass" in _plain(result.stdout)
    inspect_result = runner.invoke(
        app,
        ["anchor", "inspect-gate", "--diagnostics-directory", str(diagnostics)],
    )
    assert inspect_result.exit_code == 0
    assert "gate=pass" in _plain(inspect_result.stdout)


def _historical_fixture_roots(tmp_path: Path) -> tuple[Path, Path]:
    shared_root = tmp_path / "shared_threshold"
    local_root = tmp_path / "local_threshold"
    for seed, shared_value, local_value in zip(
        range(5),
        HISTORICAL_SHARED_THRESHOLD_CV_FPR,
        HISTORICAL_LOCAL_THRESHOLD_CV_FPR,
        strict=True,
    ):
        identity = f"{seed:064d}"
        for root, cv_fpr, scope in (
            (shared_root, shared_value.value, "eligible_client_arithmetic_mean"),
            (local_root, local_value.value, "per_client_percentile"),
        ):
            path = root / f"seed_{seed}" / "metrics.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                dumps(
                    {
                        "seed": Seed(seed).value,
                        "dataset": "nbaiot",
                        "regime": "a",
                        "threshold_scope": scope,
                        "cv_fpr": cv_fpr,
                        "client_count": 9,
                        "eligible_count": 9,
                        "provenance": {
                            "model_checkpoint_identity": identity,
                            "score_artifact_identity": "s" * 64,
                            "split_manifest_identity": "p" * 64,
                            "config_identity": "c" * 64,
                            "metric_code_version": "m" * 64,
                            "threshold_code_version": "t" * 64,
                            "package_version": "v" * 64,
                            "generated_at_utc": "2026-05-03T00:00:00+00:00",
                        },
                    }
                ),
                encoding="utf-8",
            )
    return shared_root, local_root


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


def test_registered_run_commands_include_absorption_and_temporal_analysis() -> None:
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    output = _plain(result.stdout)
    for command in (
        "analyze-confirmatory",
        "analyze-ditto-absorption",
        "analyze-fedprox-absorption",
        "ditto-stress-test-campaign",
        "fedprox-stress-test-seed",
        "fedprox-coefficient-campaign",
        "fedprox-grid-campaign",
        "analyze-temporal-campaign",
        "analyze-edge-benign-equity",
        "analyze-ciciot-file-client-boundary",
    ):
        assert command in output


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
