import ast
from pathlib import Path


def test_only_storage_adapters_and_the_provenance_inventory_construct_filesystem_paths() -> None:
    source_root = Path("src/datp_core")
    allowed_roots = (
        source_root / "infrastructure" / "data",
        source_root / "infrastructure" / "persistence",
    )
    allowed_modules = (source_root / "infrastructure" / "runtime" / "provenance.py",)
    for module in source_root.rglob("*.py"):
        tree = ast.parse(module.read_text())
        if _imports_pathlib(tree):
            assert _is_allowed_path_module(module, allowed_roots, allowed_modules)


def _imports_pathlib(tree: ast.AST) -> bool:
    return any(_is_pathlib_import(node) for node in ast.walk(tree))


def _is_pathlib_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(alias.name == "pathlib" for alias in node.names)
    return isinstance(node, ast.ImportFrom) and node.module == "pathlib"


def _is_allowed_path_module(module: Path, allowed_roots: tuple[Path, ...], allowed_modules: tuple[Path, ...]) -> bool:
    return module in allowed_modules or any(module.is_relative_to(allowed_root) for allowed_root in allowed_roots)


def test_application_does_not_import_the_internal_resolver() -> None:
    application_source = Path("src/datp_core/application")
    assert all("ArtifactPathResolver" not in module.read_text() for module in application_source.rglob("*.py"))
