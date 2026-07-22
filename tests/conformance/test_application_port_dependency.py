from __future__ import annotations

import ast
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "datp_core"

_FORBIDDEN_INFRASTRUCTURE_IMPORTS = {
    "datp_core.infrastructure.datasets.nbaiot",
    "datp_core.infrastructure.datasets.ciciot2023",
    "datp_core.infrastructure.querying.audit_service",
    "datp_core.infrastructure.thresholding.estimators",
}


def _relative(path: Path) -> str:
    return path.relative_to(_SRC_ROOT).as_posix()


def test_application_does_not_import_concrete_infrastructure_modules() -> None:
    """Application use cases must not import concrete dataset/query/threshold implementations."""
    application_dir = _SRC_ROOT / "application"
    offenders: list[tuple[str, str]] = []

    for path in sorted(application_dir.rglob("*.py")):
        rel = _relative(path)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module is not None:
                if node.module in _FORBIDDEN_INFRASTRUCTURE_IMPORTS:
                    offenders.append((rel, node.module))

    assert offenders == [], f"Application layer imports concrete infrastructure: {offenders}"


def test_stage_handler_has_no_dataset_specific_branch() -> None:
    """The data stage handler must not branch on dataset_id string values."""
    data_stages_path = _SRC_ROOT / "application" / "data_stages.py"
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
                    f"data_stages.py line {i} contains dataset-specific string '{pattern}': {stripped}"
                )
