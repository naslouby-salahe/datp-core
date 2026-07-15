import ast
from pathlib import Path

import pytest

SOURCE_ROOT = Path("src/datp_core")


@pytest.mark.architecture
def test_source_import_graph_contains_no_cycles() -> None:
    graph = _build_import_graph()
    for module in graph:
        _visit(module, graph, visited=set(), active=())


def test_cycle_detector_rejects_an_adversarial_graph() -> None:
    with pytest.raises(AssertionError, match="import cycle"):
        _visit("a", {"a": ("b",), "b": ("a",)}, visited=set(), active=())


def _build_import_graph() -> dict[str, tuple[str, ...]]:
    modules = {_module_name(path) for path in SOURCE_ROOT.rglob("*.py")}
    return {
        _module_name(path): tuple(
            target for imported in _imports(path) if (target := _known_module(imported, modules)) is not None
        )
        for path in SOURCE_ROOT.rglob("*.py")
    }


def _visit(module: str, graph: dict[str, tuple[str, ...]], visited: set[str], active: tuple[str, ...]) -> None:
    if module in active:
        raise AssertionError(f"import cycle: {' -> '.join((*active, module))}")
    if module in visited:
        return
    visited.add(module)
    for target in graph[module]:
        _visit(target, graph, visited, (*active, module))


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    return ".".join(("datp_core", *parts))


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text())
    direct = tuple(alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names)
    from_imports = tuple(
        node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    return (*direct, *from_imports)


def _known_module(module: str, modules: set[str]) -> str | None:
    candidates = tuple(candidate for candidate in modules if module == candidate or module.startswith(candidate + "."))
    return max(candidates, key=len) if candidates else None
