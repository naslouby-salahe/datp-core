import pytest
from typer.testing import CliRunner

from datp_core.app.campaign import PreprocessResult
from datp_core.app.cli.app import app
from datp_core.core.identifiers import DatasetId

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


def test_preprocess_without_dataset_identifier_preprocesses_all_datasets(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[DatasetId | None] = []

    def fake_preprocess(
        dataset_id: DatasetId | None,
        *,
        overwrite: object,
        progress: object | None = None,
    ) -> PreprocessResult:
        captured.append(dataset_id)
        return PreprocessResult(
            datasets=(DatasetId.NBAIOT, DatasetId.CICIOT2023, DatasetId.EDGE_IIOTSET),
            publications=(),
        )

    monkeypatch.setattr("datp_core.app.cli.app.preprocess_datasets", fake_preprocess)
    result = RUNNER.invoke(app, ["preprocess"])
    assert result.exit_code == 0
    assert captured == [None]


def test_preprocess_with_dataset_identifier_preprocesses_only_that_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[DatasetId | None] = []

    def fake_preprocess(
        dataset_id: DatasetId | None,
        *,
        overwrite: object,
        progress: object | None = None,
    ) -> PreprocessResult:
        captured.append(dataset_id)
        assert dataset_id is not None
        return PreprocessResult(datasets=(dataset_id,), publications=())

    monkeypatch.setattr("datp_core.app.cli.app.preprocess_datasets", fake_preprocess)
    result = RUNNER.invoke(app, ["preprocess", "nbaiot"])
    assert result.exit_code == 0
    assert captured == [DatasetId.NBAIOT]
