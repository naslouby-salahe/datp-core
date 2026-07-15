import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_analysis_specifications_import_only_analysis_and_domain_modules() -> None:
    analysis_root = Path(__file__).parents[2] / "src" / "datp_core" / "analysis"
    for module in analysis_root.rglob("*.py"):
        imported_modules = _imported_modules(ast.parse(module.read_text()))
        assert all(imported.startswith(("datp_core.analysis", "datp_core.domain")) for imported in imported_modules), (
            module
        )


@pytest.mark.architecture
def test_analysis_specifications_exclude_frameworks_persistence_paths_and_sankey() -> None:
    analysis_root = Path(__file__).parents[2] / "src" / "datp_core" / "analysis"
    forbidden_fragments = ("matplotlib", "pandas", "pyarrow", "numpy", "torch", "scipy", "sklearn", "pathlib", "sankey")
    for module in analysis_root.rglob("*.py"):
        source = module.read_text().casefold()
        assert not any(fragment in source for fragment in forbidden_fragments), module


def _imported_modules(tree: ast.AST) -> tuple[str, ...]:
    return tuple(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None and node.module.startswith("datp_core")
    )
