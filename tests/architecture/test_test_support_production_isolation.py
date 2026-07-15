import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_production_modules_never_import_test_support() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"

    for source_file in source_root.rglob("*.py"):
        module = ast.parse(source_file.read_text())
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                assert all(not alias.name.startswith("tests.support") for alias in node.names)
            if isinstance(node, ast.ImportFrom):
                assert node.module is None or not node.module.startswith("tests.support")
