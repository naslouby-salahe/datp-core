import ast
from pathlib import Path

_COMPOSITION_MODULES = (
    Path("src/datp_core/composition/root.py"),
    Path("src/datp_core/composition/registries.py"),
)
_FRAMEWORK_TOP_LEVEL_MODULES = frozenset(
    {
        "matplotlib",
        "msgspec",
        "numpy",
        "pandas",
        "pyarrow",
        "scipy",
        "sklearn",
        "torch",
    }
)


def test_composition_has_no_direct_framework_import() -> None:
    for module_path in _COMPOSITION_MODULES:
        tree = ast.parse(module_path.read_text())
        imported_modules = tuple(
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (node.names if isinstance(node, ast.Import) else (() if node.module is None else ()))
        )
        imported_modules += tuple(
            node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None
        )

        assert all(module.split(".")[0] not in _FRAMEWORK_TOP_LEVEL_MODULES for module in imported_modules)


def test_composition_collectively_reaches_the_allowed_layers_without_a_locator() -> None:
    source = "\n".join(module_path.read_text() for module_path in _COMPOSITION_MODULES)

    assert "datp_core.application" in source
    assert "datp_core.config" in source
    assert "datp_core.domain" in source
    assert "datp_core.infrastructure" in source
    assert ".get(" not in source
