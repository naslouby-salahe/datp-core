import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_application_analysis_exception_is_confined_to_the_trace_payload_contract() -> None:
    application_root = Path(__file__).parents[2] / "src" / "datp_core" / "application"
    analysis_importers = tuple(
        path.relative_to(application_root)
        for path in application_root.rglob("*.py")
        if any(module.startswith("datp_core.analysis") for module in _imports(path))
    )

    assert analysis_importers == (Path("reporting/contracts.py"),)


@pytest.mark.architecture
def test_plotting_is_confined_to_the_matplotlib_renderer_and_no_sankey_route_exists() -> None:
    source_root = Path(__file__).parents[2] / "src" / "datp_core"
    plotting_importers = tuple(
        path.relative_to(source_root)
        for path in source_root.rglob("*.py")
        if any(module.startswith("matplotlib") for module in _imports(path))
    )

    assert plotting_importers == (Path("infrastructure/reporting/matplotlib.py"),)
    assert not any("sankey" in path.read_text().casefold() for path in source_root.rglob("*.py"))


def _imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text())
    imported_from = tuple(
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    direct_imports = tuple(
        alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
    )
    return (*imported_from, *direct_imports)
