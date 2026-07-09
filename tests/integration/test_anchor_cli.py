from dataclasses import replace

from datp_core import cli
from datp_core.utils.paths import resolve_paths


def test_anchor_cli_smoke_plan_and_missing_data_gate(tmp_path, monkeypatch, capsys):
    original = resolve_paths()
    paths = replace(
        original,
        data_raw=tmp_path / "raw",
        outputs=tmp_path / "outputs",
        checkpoints=tmp_path / "checkpoints",
        outputs_scores=tmp_path / "outputs" / "scores",
        outputs_metrics=tmp_path / "outputs" / "metrics",
        outputs_manifests=tmp_path / "outputs" / "manifests",
        outputs_logs=tmp_path / "outputs" / "logs",
        outputs_tables=tmp_path / "outputs" / "tables",
        outputs_figures=tmp_path / "outputs" / "figures",
    )
    monkeypatch.setattr(cli, "resolve_paths", lambda: paths)
    assert cli.main(["run-smoke", "anchor-fixture"]) == 0
    assert "fixture anchor smoke complete" in capsys.readouterr().out
    score_path = paths.outputs / "anchor-fixture" / "seed-0" / "scores.npz"
    assert cli.main(["run-thresholds", str(score_path)]) == 0
    assert "threshold-only run complete" in capsys.readouterr().out
    assert cli.main(["plan", "confirmatory-regime-a"]) == 0
    assert capsys.readouterr().out.count("policy=") == 20
    assert cli.main(["run-mini", "confirmatory-regime-a", "--seeds", "2"]) == 2
    assert "raw data is missing" in capsys.readouterr().err
    assert cli.main(["validate-anchor-readiness"]) == 2
    assert "BLOCKED" in capsys.readouterr().out
    assert cli.main(["run-full", "confirmatory-regime-a"]) == 1
    assert "confirm-full-run" in capsys.readouterr().err
