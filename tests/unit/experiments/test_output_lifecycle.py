from __future__ import annotations

import os
from pathlib import Path

import pytest

from datp_core.core.identifiers import ExperimentId
from datp_core.experiments.execution.output_manager import ExperimentOutputManager, OutputState


def _finalize(manager: ExperimentOutputManager, experiment_id: ExperimentId) -> None:
    directory = manager.begin(experiment_id)
    frozen = directory / "frozen_result"
    frozen.mkdir()
    (frozen / "result.json").write_text('{"anchor_equivalence_passed": true}', encoding="utf-8")
    reports = directory / "reports"
    reports.mkdir()
    (reports / "summary.md").write_text("report", encoding="utf-8")
    manager.finalize_from_directory(
        experiment_id,
        scientific_fingerprint="science",
        execution_fingerprint="execution",
        source_data_fingerprint="source",
        prerequisite_result_fingerprints={},
        started_at=1.0,
    )


def test_final_output_requires_frozen_result_reports_and_checksum_inventory(tmp_path: Path) -> None:
    manager = ExperimentOutputManager(tmp_path)
    experiment_id = ExperimentId("anchor")
    _finalize(manager, experiment_id)

    inspection = manager.inspect(
        experiment_id,
        scientific_fingerprint="science",
        execution_fingerprint="execution",
        source_data_fingerprint="source",
        prerequisite_result_fingerprints={},
    )

    assert inspection.state is OutputState.VALID_COMPLETED
    assert inspection.manifest is not None
    assert inspection.manifest.code_revision
    assert inspection.manifest.frozen_result_path == "frozen_result/result.json"
    assert inspection.manifest.report_paths == ("reports/summary.md",)


def test_completed_output_with_changed_direct_file_is_corrupt(tmp_path: Path) -> None:
    manager = ExperimentOutputManager(tmp_path)
    experiment_id = ExperimentId("anchor")
    _finalize(manager, experiment_id)
    (manager.experiment_dir(experiment_id) / "reports" / "summary.md").write_text("changed", encoding="utf-8")

    assert manager.inspect(experiment_id).state is OutputState.CORRUPT


def test_finalization_accepts_the_planner_frozen_result_location(tmp_path: Path) -> None:
    manager = ExperimentOutputManager(tmp_path)
    experiment_id = ExperimentId("planner-location")
    directory = manager.begin(experiment_id)
    (directory / "frozen-result.json").write_text('{"outcomes": {}}', encoding="utf-8")
    reports = directory / "reports"
    reports.mkdir()
    (reports / "report.md").write_text("report", encoding="utf-8")

    manifest = manager.finalize_from_directory(
        experiment_id,
        scientific_fingerprint="science",
        execution_fingerprint="execution",
        source_data_fingerprint="source",
        prerequisite_result_fingerprints={},
        started_at=1.0,
    )

    assert manifest.frozen_result_path == "frozen-result.json"


def test_delete_is_scoped_to_the_selected_experiment(tmp_path: Path) -> None:
    manager = ExperimentOutputManager(tmp_path)
    selected = ExperimentId("selected")
    other = ExperimentId("other")
    manager.begin(selected)
    manager.begin(other)

    manager.delete(selected)

    assert not manager.exists(selected)
    assert manager.exists(other)


def test_completed_marker_must_not_precede_the_final_manifest(tmp_path: Path) -> None:
    manager = ExperimentOutputManager(tmp_path)
    experiment_id = ExperimentId("anchor")
    _finalize(manager, experiment_id)
    directory = manager.experiment_dir(experiment_id)
    marker = directory / "COMPLETED"
    manifest = directory / "manifest.json"

    marker_time = marker.stat().st_mtime_ns
    os.utime(manifest, ns=(marker_time + 1, marker_time + 1))

    inspection = manager.inspect(experiment_id)

    assert inspection.state is OutputState.CORRUPT
    assert inspection.reason is not None
    assert "COMPLETED" in inspection.reason


def test_delete_rejects_a_symlinked_output_root(tmp_path: Path) -> None:
    safe_target = tmp_path / "safe-target"
    safe_target.mkdir()
    symlink_root = tmp_path / "outputs-link"
    symlink_root.symlink_to(safe_target, target_is_directory=True)
    manager = ExperimentOutputManager(symlink_root)

    with pytest.raises(ValueError, match="symlinked output root"):
        manager.delete(ExperimentId("selected"))


def test_delete_rejects_a_symlinked_experiments_directory(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    output_root.mkdir()
    external_experiments = tmp_path / "external-experiments"
    external_experiments.mkdir()
    (output_root / "experiments").symlink_to(external_experiments, target_is_directory=True)
    manager = ExperimentOutputManager(output_root)

    with pytest.raises(ValueError, match="symlinked experiments"):
        manager.delete(ExperimentId("selected"))


def test_delete_rejects_a_symlinked_experiment_directory(tmp_path: Path) -> None:
    output_root = tmp_path / "outputs"
    experiments_root = output_root / "experiments"
    experiments_root.mkdir(parents=True)
    external_experiment = tmp_path / "external-experiment"
    external_experiment.mkdir()
    (experiments_root / "selected").symlink_to(external_experiment, target_is_directory=True)
    manager = ExperimentOutputManager(output_root)

    with pytest.raises(ValueError, match="unsafe experiment output"):
        manager.delete(ExperimentId("selected"))

    assert external_experiment.exists()


def test_delete_rejects_a_non_directory_experiment_target(tmp_path: Path) -> None:
    manager = ExperimentOutputManager(tmp_path)
    target = manager.experiment_dir(ExperimentId("selected"))
    target.parent.mkdir(parents=True)
    target.write_text("not a directory", encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe experiment output"):
        manager.delete(ExperimentId("selected"))

    assert target.exists()


def test_delete_shared_outputs_preserves_experiments_preprocessing_and_unrelated_files(tmp_path: Path) -> None:
    manager = ExperimentOutputManager(tmp_path)
    manager.begin(ExperimentId("selected"))
    shared_file = tmp_path / "shared" / "scores" / "score.parquet"
    shared_file.parent.mkdir(parents=True)
    shared_file.write_bytes(b"shared")
    preprocessing = tmp_path / "preprocessing" / "fit.json"
    preprocessing.parent.mkdir(parents=True)
    preprocessing.write_text("fit", encoding="utf-8")
    unrelated = tmp_path / "unrelated.txt"
    unrelated.write_text("preserve", encoding="utf-8")

    manager.delete_shared_outputs()

    assert not (tmp_path / "shared").exists()
    assert manager.exists(ExperimentId("selected"))
    assert preprocessing.read_text(encoding="utf-8") == "fit"
    assert unrelated.read_text(encoding="utf-8") == "preserve"
