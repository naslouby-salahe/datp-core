"""Exercises `datp-core doctor` as a real subprocess, end to end, against the
checked-out repository. Never requires raw datasets to be present."""

import subprocess
import sys
from pathlib import Path

from datp_core.utils.paths import find_repo_root

REPO_ROOT = find_repo_root(Path(__file__))


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    script = "from datp_core.cli import main; import sys; sys.exit(main(sys.argv[1:]))"
    return subprocess.run(
        [sys.executable, "-c", script, *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_doctor_subprocess_exits_cleanly_without_raw_datasets():
    result = _run_cli("doctor")
    assert result.returncode == 0, result.stderr
    assert "repo_root:" in result.stdout
    assert "device:" in result.stdout
    assert "MISSING" in result.stdout
    assert "layout: OK" in result.stdout


def _data_raw_listing() -> list[str]:
    data_raw = REPO_ROOT / "data" / "raw"
    if not data_raw.exists():
        return []
    return sorted(p.name for p in data_raw.glob("*"))


def test_doctor_subprocess_never_writes_to_data_raw():
    before = _data_raw_listing()
    _run_cli("doctor")
    after = _data_raw_listing()
    assert before == after


def test_help_subprocess_lists_every_phase1_command():
    result = _run_cli("--help")
    assert result.returncode == 0
    for command in ("doctor", "validate-config", "show-paths", "list-suites", "validate-layout"):
        assert command in result.stdout
    assert "train" not in result.stdout
