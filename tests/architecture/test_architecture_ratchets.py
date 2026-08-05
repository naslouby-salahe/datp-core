import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "datp_core"
TEST_ROOT = REPOSITORY_ROOT / "tests"
CAPABILITY_PACKAGES = (
    "datasets",
    "populations",
    "preprocessing",
    "learning",
    "calibration",
    "thresholding",
    "evaluation",
    "analysis",
    "anchor",
)
FORBIDDEN_LEGACY_PATHS = (
    SOURCE_ROOT / "cli.py",
    SOURCE_ROOT / "orchestration" / "commands",
    SOURCE_ROOT / "orchestration" / "stages",
)


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts))


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    return tuple(imports)


def test_legacy_execution_spines_cannot_return() -> None:
    assert all(not path.exists() for path in FORBIDDEN_LEGACY_PATHS)
    violations = tuple(
        str(path.relative_to(REPOSITORY_ROOT))
        for root in (SOURCE_ROOT, TEST_ROOT)
        for path in _python_files(root)
        if any(
            imported.startswith("datp_core.orchestration.commands")
            or imported.startswith("datp_core.orchestration.stages")
            for imported in _imports(path)
        )
    )
    assert not violations


def test_domain_imports_no_higher_layer() -> None:
    violations = tuple(
        f"{path.relative_to(REPOSITORY_ROOT)} imports {imported}"
        for path in _python_files(SOURCE_ROOT / "domain")
        for imported in _imports(path)
        if imported.startswith("datp_core.") and not imported.startswith("datp_core.domain")
    )
    assert not violations, "\n".join(violations)


def test_protocols_depend_only_on_domain() -> None:
    violations = tuple(
        f"{path.relative_to(REPOSITORY_ROOT)} imports {imported}"
        for path in _python_files(SOURCE_ROOT / "protocols")
        for imported in _imports(path)
        if imported.startswith("datp_core.")
        and not imported.startswith(("datp_core.domain", "datp_core.protocols"))
    )
    assert not violations, "\n".join(violations)


def test_capabilities_never_import_pipeline_or_adapters() -> None:
    forbidden = (
        "datp_core.pipeline",
        "datp_core.orchestration",
        "datp_core.cli",
        "datp_core.reporting",
    )
    violations = tuple(
        f"{path.relative_to(REPOSITORY_ROOT)} imports {imported}"
        for package in CAPABILITY_PACKAGES
        for path in _python_files(SOURCE_ROOT / package)
        for imported in _imports(path)
        if imported.startswith(forbidden)
    )
    assert not violations, "\n".join(violations)


def test_cli_and_orchestration_use_pipeline_entry_points() -> None:
    adapter_roots = (SOURCE_ROOT / "cli", SOURCE_ROOT / "orchestration")
    violations = tuple(
        str(path.relative_to(REPOSITORY_ROOT))
        for root in adapter_roots
        for path in _python_files(root)
        if path.name not in {"__init__.py", "resources.py", "hooks.py", "definitions.py", "jobs.py"}
        and not any(imported.startswith("datp_core.pipeline") for imported in _imports(path))
    )
    assert not violations
