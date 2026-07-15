import ast
from pathlib import Path

PORT_MODULES = (
    Path("src/datp_core/application/ports/persistence.py"),
    Path("src/datp_core/application/ports/runtime.py"),
)


def test_persistence_runtime_ports_exclude_path_and_framework_carriers() -> None:
    forbidden_imports = {
        "pathlib",
        "numpy",
        "pandas",
        "pyarrow",
        "torch",
        "sklearn",
        "flower",
    }
    for module in PORT_MODULES:
        tree = ast.parse(module.read_text())
        imported_modules = {
            alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
        }
        imported_modules.update(
            node.module.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module is not None
        )
        assert not imported_modules & forbidden_imports
        assert "ArtifactRepository" not in module.read_text()
        assert "ArtifactPathResolver" not in module.read_text()


def test_persistence_ports_remain_semantically_narrow() -> None:
    source = Path("src/datp_core/application/ports/persistence.py").read_text()
    assert "def save_recovery" in source
    assert "def load_recovery" in source
    assert "def save(" in source
    assert "def load(" not in source
