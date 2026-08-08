"""Final architecture boundaries: deleted ownership must not return."""

from ast import Import, ImportFrom, parse
from pathlib import Path


SOURCE_ROOT = Path(__file__).resolve().parents[3] / "src" / "datp_core"


def _imports(path: Path) -> tuple[str, ...]:
    tree = parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in tree.body:
        if isinstance(node, ImportFrom) and node.module is not None:
            modules.append(node.module)
        elif isinstance(node, Import):
            modules.extend(alias.name for alias in node.names)
    return tuple(modules)


def test_deleted_architectures_do_not_exist() -> None:
    assert not (SOURCE_ROOT / "cli").exists()
    assert not (SOURCE_ROOT / "reporting").exists()
    assert not (SOURCE_ROOT / "pipeline" / "workflows").exists()
    assert not (SOURCE_ROOT / "pipeline" / "planning.py").exists()
    assert not (SOURCE_ROOT / "app" / "campaign.py").exists()
    assert not (SOURCE_ROOT / "experiments" / "planning.py").exists()


def test_source_does_not_import_deleted_module_paths() -> None:
    forbidden = (
        "datp_core.cli",
        "datp_core.reporting",
        "datp_core.pipeline.workflows",
        "datp_core.pipeline.planning",
        "datp_core.app.campaign",
        "datp_core.experiments.planning",
    )
    offenders = tuple(
        path.relative_to(SOURCE_ROOT)
        for path in SOURCE_ROOT.rglob("*.py")
        if any(
            imported == prefix or imported.startswith(f"{prefix}.")
            for imported in _imports(path)
            for prefix in forbidden
        )
    )
    assert offenders == ()


def test_only_cli_package_may_import_typer() -> None:
    offenders = tuple(
        path.relative_to(SOURCE_ROOT)
        for path in SOURCE_ROOT.rglob("*.py")
        if "typer" in _imports(path) and (SOURCE_ROOT / "app" / "cli") not in path.parents
    )
    assert offenders == ()
