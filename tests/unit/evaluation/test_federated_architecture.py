from ast import Import, ImportFrom, parse
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[3] / "src" / "datp_core"


def _imported_modules(path: Path) -> tuple[str, ...]:
    modules: list[str] = []
    for node in parse(path.read_text(encoding="utf-8"), filename=str(path)).body:
        if isinstance(node, ImportFrom) and node.module is not None:
            modules.append(node.module)
        elif isinstance(node, Import):
            modules.extend(alias.name for alias in node.names)
    return tuple(modules)


def test_federated_analysis_separates_metrics_execution_and_publication() -> None:
    metrics = _SOURCE_ROOT / "analysis" / "metrics"

    assert (metrics / "population.py").is_file()
    assert (metrics / "federated.py").is_file()
    assert (metrics / "federated_execution.py").is_file()
    assert (metrics / "federated_publication.py").is_file()
    assert "polars" not in _imported_modules(metrics / "federated.py")

    direct_importers = tuple(
        path.relative_to(_SOURCE_ROOT)
        for path in _SOURCE_ROOT.rglob("*.py")
        if "datp_core.analysis.metrics.population" in _imported_modules(path)
    )
    assert direct_importers
