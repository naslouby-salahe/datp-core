import ast
from pathlib import Path

import pytest

STAGES_DIRECTORY = Path("src/datp_core/application/stages")
EXPECTED_STAGE_MODULES = (
    "inspect_dataset",
    "partition_clients",
    "build_splits",
    "fit_preprocessor",
    "materialize_splits",
    "train_model",
    "select_checkpoint",
    "generate_scores",
    "construct_thresholds",
    "evaluate_policy",
    "analyze_statistics",
)
FORBIDDEN_IMPORT_PREFIXES = (
    "datp_core.infrastructure",
    "numpy",
    "pandas",
    "pyarrow",
    "scipy",
    "torch",
    "flower",
)


@pytest.mark.architecture
def test_stage_directory_has_the_architecture_locked_module_set() -> None:
    stage_modules = {path.stem for path in STAGES_DIRECTORY.glob("*.py") if path.name != "__init__.py"}

    assert stage_modules == set(EXPECTED_STAGE_MODULES)
    assert "partition_and_preprocess" not in stage_modules


@pytest.mark.architecture
def test_stage_modules_import_only_application_ports_or_domain_types() -> None:
    for path in STAGES_DIRECTORY.glob("*.py"):
        if path.name == "__init__.py":
            continue
        imports = _imports_for(path)
        assert _uses_only_stage_layer_dependencies(imports), path
        assert _has_no_framework_imports(imports), path


def _imports_for(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text())
    imported_modules = tuple(
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    direct_imports = tuple(
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    )
    return (*imported_modules, *direct_imports)


def _uses_only_stage_layer_dependencies(imports: tuple[str, ...]) -> bool:
    return all(
        not imported.startswith("datp_core") or imported.startswith(("datp_core.application.ports", "datp_core.domain"))
        for imported in imports
    )


def _has_no_framework_imports(imports: tuple[str, ...]) -> bool:
    return not any(imported.startswith(prefix) for imported in imports for prefix in FORBIDDEN_IMPORT_PREFIXES)
