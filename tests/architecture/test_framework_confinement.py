import ast
from pathlib import Path

import pytest

SOURCE_ROOT = Path("src/datp_core")
FRAMEWORK_LAYERS = {
    "filelock": "infrastructure",
    "flwr": "infrastructure",
    "matplotlib": "infrastructure",
    "msgspec": "infrastructure",
    "numpy": "infrastructure",
    "pandas": "infrastructure",
    "pydantic": "config",
    "pyarrow": "infrastructure",
    "rich": "cli",
    "scipy": "infrastructure",
    "sklearn": "infrastructure",
    "structlog": "infrastructure",
    "torch": "infrastructure",
    "yaml": "config",
}


@pytest.mark.architecture
def test_framework_imports_remain_in_their_authorized_layer() -> None:
    assert not _framework_violations(SOURCE_ROOT)


@pytest.mark.architecture
def test_application_ports_have_no_framework_or_adapter_boundary_types() -> None:
    forbidden_fragments = tuple(FRAMEWORK_LAYERS) + ("datp_core.infrastructure",)
    for path in (SOURCE_ROOT / "application" / "ports").glob("*.py"):
        source = path.read_text().casefold()
        assert not any(fragment in source for fragment in forbidden_fragments), path


def test_framework_confinement_rejects_an_adversarial_wrong_layer_import(tmp_path: Path) -> None:
    module = tmp_path / "application" / "bad.py"
    module.parent.mkdir()
    module.write_text("import torch\n")

    assert _framework_violations(tmp_path) == ((module, "torch"),)


def _framework_violations(root: Path) -> tuple[tuple[Path, str], ...]:
    violations: list[tuple[Path, str]] = []
    for path in root.rglob("*.py"):
        for module in _imports(path):
            framework = module.split(".")[0]
            if framework in FRAMEWORK_LAYERS and _layer(path, root) != FRAMEWORK_LAYERS[framework]:
                violations.append((path, module))
    return tuple(violations)


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text())
    direct = tuple(alias.name for node in tree.body if isinstance(node, ast.Import) for alias in node.names)
    from_imports = tuple(
        node.module for node in tree.body if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    return (*direct, *from_imports)


def _layer(path: Path, root: Path) -> str:
    return path.relative_to(root).parts[0]
