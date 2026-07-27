"""AST static architecture checks for datp_core.analysis."""

from __future__ import annotations

import ast
from pathlib import Path

ANALYSIS_PKG = Path(__file__).resolve().parents[3] / "src" / "datp_core" / "analysis"


def test_ast_forbidden_patterns_in_analysis_package() -> None:
    for py_file in ANALYSIS_PKG.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        rel_path = py_file.relative_to(ANALYSIS_PKG)

        # Check for forbidden strings in raw content
        assert "AnalysisInputBundle" not in content, f"Forbidden 'AnalysisInputBundle' found in {rel_path}"
        assert "_evaluation_context" not in content, f"Forbidden '_evaluation_context' found in {rel_path}"
        assert "context: AnalysisExecutionContext | None" not in content, (
            f"Forbidden dual architecture found in {rel_path}"
        )
        assert "TODO" not in content, f"Forbidden 'TODO' found in {rel_path}"
        assert "FIXME" not in content, f"Forbidden 'FIXME' found in {rel_path}"
        assert "raise ValueError" not in content, f"Forbidden 'raise ValueError' found in {rel_path}"
        assert "raise RuntimeError" not in content, f"Forbidden 'raise RuntimeError' found in {rel_path}"

        tree = ast.parse(content, filename=str(py_file))

        # Inspect AST for specific imports and constructs
        for node in ast.walk(tree):
            # Check internal __all__
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "__all__":
                        pytest_fail = f"Forbidden internal __all__ assignment found in {rel_path}"
                        raise AssertionError(pytest_fail)

            # Check capability specific AST rules (excluding runtime/ and contracts.py/enums.py/errors.py)
            if "runtime" not in py_file.parts:
                if isinstance(node, ast.ImportFrom):
                    assert "ArtifactStore" not in [alias.name for alias in node.names], (
                        f"Capability file {rel_path} must not import ArtifactStore"
                    )
                    assert "BytesIO" not in [alias.name for alias in node.names], (
                        f"Capability file {rel_path} must not import BytesIO"
                    )
                    assert "StageJobContext" not in [alias.name for alias in node.names], (
                        f"Capability file {rel_path} must not import StageJobContext"
                    )
