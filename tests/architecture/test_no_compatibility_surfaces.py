import ast
from pathlib import Path

from datp_core import __version__
from datp_core.domain.enums import CentralizedThresholdMethod, FederatedThresholdMethod


def parsed_source_files() -> tuple[tuple[Path, ast.Module], ...]:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"
    return tuple(
        (source_path, ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path)))
        for source_path in source_root.rglob("*.py")
    )


def test_no_wildcard_imports_or_compatibility_modules_exist() -> None:
    for source_path, tree in parsed_source_files():
        assert "compat" not in source_path.stem.lower()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert all(alias.name != "*" for alias in node.names), source_path


def test_package_initializers_do_not_redirect_or_reexport_domain_types() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"
    for initializer in (source_root / "__init__.py", source_root / "domain" / "__init__.py"):
        tree = ast.parse(initializer.read_text(encoding="utf-8"), filename=str(initializer))
        imports = tuple(node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)))
        assert not imports
    assert __version__ == "0.1.0"


def test_threshold_types_have_no_compatibility_alias_or_overlap() -> None:
    assert len(FederatedThresholdMethod.__members__) == len(FederatedThresholdMethod)
    assert len(CentralizedThresholdMethod.__members__) == len(CentralizedThresholdMethod)
    assert set(FederatedThresholdMethod).isdisjoint(set(CentralizedThresholdMethod))

def test_source_uses_no_explicit_any_type() -> None:
    for source_path, tree in parsed_source_files():
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert all(alias.name != "Any" for alias in node.names), source_path
            elif isinstance(node, ast.Name):
                assert node.id != "Any", source_path
            elif isinstance(node, ast.Attribute):
                assert node.attr != "Any", source_path
