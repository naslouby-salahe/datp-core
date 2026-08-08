from ast import Import, ImportFrom, parse
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "datp_core"
_RETIRED_OWNERS = frozenset(
    {
        "calibration",
        "datasets",
        "domain",
        "evaluation",
        "learning",
        "pipeline",
        "preprocessing",
        "thresholding",
    }
)


def _imported_modules(path: Path) -> tuple[str, ...]:
    tree = parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in tree.body:
        if isinstance(node, ImportFrom) and node.module is not None:
            modules.append(node.module)
        elif isinstance(node, Import):
            modules.extend(alias.name for alias in node.names)
    return tuple(modules)


def test_retired_ownership_packages_are_absent() -> None:
    assert all(not (_SOURCE_ROOT / owner).exists() for owner in _RETIRED_OWNERS)


def test_production_modules_do_not_import_retired_owners() -> None:
    forbidden = tuple(f"datp_core.{owner}" for owner in _RETIRED_OWNERS)
    violations = {
        path.relative_to(_SOURCE_ROOT): module
        for path in _SOURCE_ROOT.rglob("*.py")
        for module in _imported_modules(path)
        if module.startswith(forbidden)
    }
    assert not violations


def test_canonical_packages_own_the_scientific_cutover() -> None:
    for owner in (
        "core",
        "protocols",
        "runtime",
        "artifacts",
        "data",
        "detector",
        "thresholds",
        "analysis",
        "experiments",
    ):
        assert (_SOURCE_ROOT / owner).is_dir()


def test_cli_surface_is_research_facing_only() -> None:
    cli = _SOURCE_ROOT / "cli"
    present = {path.name for path in cli.glob("*.py")}
    assert present == {"__init__.py", "app.py", "anchor.py", "execution.py", "validation.py"}
    app_text = (cli / "app.py").read_text(encoding="utf-8")
    for obsolete in (
        "confirmatory-seed",
        "materialize-datasets",
        "preprocess-federated",
        "validate-protocols",
        "training-seed",
        "partition-seed",
    ):
        assert obsolete not in app_text
