"""Final architecture boundaries: deleted ownership must not return."""

from ast import Import, ImportFrom, parse, walk
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[3] / "src" / "datp_core"


def _imports(path: Path) -> tuple[str, ...]:
    tree = parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in walk(tree):
        if isinstance(node, ImportFrom) and node.module is not None:
            modules.append(node.module)
        elif isinstance(node, Import):
            modules.extend(alias.name for alias in node.names)
    return tuple(modules)


def test_deleted_architectures_do_not_exist() -> None:
    assert not (SOURCE_ROOT / "cli").exists()
    assert not (SOURCE_ROOT / "reporting").exists()
    assert not (SOURCE_ROOT / "pipeline").exists()
    assert (SOURCE_ROOT / "app" / "campaign.py").is_file()
    assert (SOURCE_ROOT / "app" / "planning.py").is_file()
    assert (SOURCE_ROOT / "experiments" / "planning.py").is_file()


def test_source_does_not_import_deleted_module_paths() -> None:
    legacy_roots = (
        "datp_core.cli",
        "datp_core.reporting",
        "datp_core." + "pipeline",
    )
    offenders = tuple(
        path.relative_to(SOURCE_ROOT)
        for path in SOURCE_ROOT.rglob("*.py")
        if any(
            imported == prefix or imported.startswith(f"{prefix}.")
            for imported in _imports(path)
            for prefix in legacy_roots
        )
    )
    assert offenders == ()


def test_experiment_modules_do_not_import_application_layer() -> None:
    experiment_root = SOURCE_ROOT / "experiments"
    offenders = tuple(
        path.relative_to(SOURCE_ROOT)
        for path in experiment_root.rglob("*.py")
        if any(imported == "datp_core.app" or imported.startswith("datp_core.app.") for imported in _imports(path))
    )
    assert offenders == ()


def test_only_cli_package_may_import_typer() -> None:
    offenders = tuple(
        path.relative_to(SOURCE_ROOT)
        for path in SOURCE_ROOT.rglob("*.py")
        if "typer" in _imports(path) and (SOURCE_ROOT / "app" / "cli") not in path.parents
    )
    assert offenders == ()
