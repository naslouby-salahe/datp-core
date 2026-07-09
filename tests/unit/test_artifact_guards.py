import pytest

from datp_core.experiments.overwrite_guard import (
    OverwriteGuardError,
    WriteMode,
    guard_artifact_write,
    guard_results_overwrite,
)


def test_new_artifact_path_is_allowed(tmp_path):
    path = tmp_path / "new_artifact.json"
    guard_artifact_write(path, WriteMode.CREATE_NEW)


def test_existing_path_rejected_under_create_new(tmp_path):
    path = tmp_path / "existing.json"
    path.write_text("{}")
    with pytest.raises(OverwriteGuardError):
        guard_artifact_write(path, WriteMode.CREATE_NEW)


def test_resume_with_matching_manifest_allowed(tmp_path):
    path = tmp_path / "existing.json"
    path.write_text("{}")
    guard_artifact_write(
        path,
        WriteMode.RESUME_SAME_RUN_IF_MANIFEST_MATCHES,
        existing_manifest_id="run-1",
        requested_manifest_id="run-1",
    )


def test_resume_with_mismatched_manifest_rejected(tmp_path):
    path = tmp_path / "existing.json"
    path.write_text("{}")
    with pytest.raises(OverwriteGuardError):
        guard_artifact_write(
            path,
            WriteMode.RESUME_SAME_RUN_IF_MANIFEST_MATCHES,
            existing_manifest_id="run-1",
            requested_manifest_id="run-2",
        )


def test_explicit_dev_overwrite_requires_flag(tmp_path):
    path = tmp_path / "existing.json"
    path.write_text("{}")
    with pytest.raises(OverwriteGuardError):
        guard_artifact_write(path, WriteMode.OVERWRITE_ONLY_IF_EXPLICIT_AND_MARKED_DEV)
    guard_artifact_write(
        path, WriteMode.OVERWRITE_ONLY_IF_EXPLICIT_AND_MARKED_DEV, explicit_dev_flag=True
    )


def test_results_overwrite_without_matching_source_manifest_rejected(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("x")
    with pytest.raises(OverwriteGuardError):
        guard_results_overwrite(
            path,
            existing_source_manifest_id="raw-table-1",
            requested_source_manifest_id="raw-table-2",
        )


def test_results_overwrite_with_matching_source_manifest_allowed(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("x")
    guard_results_overwrite(
        path,
        existing_source_manifest_id="raw-table-1",
        requested_source_manifest_id="raw-table-1",
    )


def test_results_overwrite_with_explicit_refresh_allowed(tmp_path):
    path = tmp_path / "table.csv"
    path.write_text("x")
    guard_results_overwrite(
        path,
        existing_source_manifest_id="raw-table-1",
        requested_source_manifest_id="raw-table-DIFFERENT",
        explicit_refresh=True,
    )
