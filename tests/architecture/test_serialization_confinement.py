import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_persistence_serialization_uses_msgspec_without_pydantic() -> None:
    module = ast.parse(Path("src/datp_core/infrastructure/persistence/serialization.py").read_text())
    imports = tuple(
        alias.name for node in ast.walk(module) if isinstance(node, ast.Import) for alias in node.names
    ) + tuple(node.module for node in ast.walk(module) if isinstance(node, ast.ImportFrom) and node.module is not None)

    assert "msgspec" in imports
    assert not any(imported.startswith("pydantic") for imported in imports)
