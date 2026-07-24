from __future__ import annotations

from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "datp_core"

# All migrated stage-handler modules must exist in the new feature-oriented tree.
_STAGE_FILES = {
    "data/materialization.py",
    "pipeline/execution.py",
    "experiments/planning.py",
    "learning/checkpoints.py",
    "learning/training.py",
    "learning/scoring.py",
    "thresholding/construction.py",
    "thresholding/calibration.py",
    "evaluation/execution.py",
    "analysis/execution/handler.py",
    "reporting/execution.py",
}


def test_stage_handler_modules_exist() -> None:
    """Every migrated stage-handler module must exist in the new feature tree."""
    missing = [pkg for pkg in _STAGE_FILES if not (_SRC_ROOT / pkg).exists()]
    assert missing == [], f"Missing stage-handler modules: {missing}"


def test_stage_handler_has_no_dataset_specific_branch() -> None:
    """The data materialization stage handler must not branch on dataset_id string values."""
    data_stages_path = _SRC_ROOT / "data" / "materialization.py"
    source = data_stages_path.read_text(encoding="utf-8")
    forbidden_patterns = ['"nbaiot"', "'nbaiot'", '"ciciot2023"', "'ciciot2023'"]
    lines = source.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith('"""') or stripped.startswith("#"):
            continue
        for pattern in forbidden_patterns:
            if pattern in line:
                raise AssertionError(
                    f"materialization.py line {i} contains dataset-specific string '{pattern}': {stripped}"
                )
