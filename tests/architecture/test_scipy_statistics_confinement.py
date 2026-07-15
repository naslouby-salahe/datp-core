import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_scipy_imports_are_confined_to_the_statistics_adapter() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"
    scipy_importers = tuple(
        source_file.relative_to(source_root) for source_file in source_root.rglob("*.py") if _imports_scipy(source_file)
    )

    assert scipy_importers == (Path("infrastructure/statistics/scipy_adapter.py"),)


def _imports_scipy(source_file: Path) -> bool:
    tree = ast.parse(source_file.read_text(), filename=str(source_file))
    return any(_is_scipy_import(node) for node in ast.walk(tree))


def _is_scipy_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(_is_scipy_module(name.name) for name in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return _is_scipy_module(node.module)
    return False


def _is_scipy_module(module: str) -> bool:
    return module == "scipy" or module.startswith("scipy.")
