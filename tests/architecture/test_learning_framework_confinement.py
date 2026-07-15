import ast
from pathlib import Path

LEARNING_FRAMEWORKS = ("torch", "flwr")


def test_application_learning_boundary_does_not_expose_pytorch_module_handles() -> None:
    application_root = Path("src/datp_core/application")

    assert all(not _mentions_learning_framework(module) for module in application_root.rglob("*.py"))


def _mentions_learning_framework(module: Path) -> bool:
    source = module.read_text()
    return "nn.Module" in source or _imports_learning_framework(ast.parse(source))


def _imports_learning_framework(tree: ast.AST) -> bool:
    return any(_is_learning_framework_import(node) for node in ast.walk(tree))


def _is_learning_framework_import(node: ast.AST) -> bool:
    if isinstance(node, ast.Import):
        return any(_is_learning_framework_module(alias.name) for alias in node.names)
    if isinstance(node, ast.ImportFrom) and node.module is not None:
        return _is_learning_framework_module(node.module)
    return False


def _is_learning_framework_module(module: str) -> bool:
    return any(module == framework or module.startswith(f"{framework}.") for framework in LEARNING_FRAMEWORKS)
