import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_provenance_timestamp_source_is_confined_to_the_system_clock() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"
    violations: list[Path] = []
    for module in source_root.rglob("*.py"):
        tree = ast.parse(module.read_text())
        if _uses_wall_clock(tree) and module.name != "provenance.py":
            violations.append(module)
    assert not violations


@pytest.mark.architecture
def test_stage_identity_modules_do_not_reference_environment_provenance_facts() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core" / "domain" / "artifacts"
    forbidden = ("CodeState", "DependencyLockState", "EnvironmentInventory")
    for module_name in ("lineage.py", "references.py"):
        source = (source_root / module_name).read_text()
        assert not any(name in source for name in forbidden)


def _uses_wall_clock(tree: ast.AST) -> bool:
    return any(_is_wall_clock_call(node) for node in ast.walk(tree))


def _is_wall_clock_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
        return False
    return isinstance(node.func.value, ast.Name) and (node.func.value.id, node.func.attr) in {
        ("datetime", "now"),
        ("datetime", "utcnow"),
        ("time", "time"),
    }
