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


def test_federated_evaluation_separates_contracts_execution_and_publication() -> None:
    evaluation = _SOURCE_ROOT / "evaluation"
    federated = evaluation / "federated"

    assert not (evaluation / "population.py").exists()
    assert (federated / "contracts.py").is_file()
    assert (federated / "execution.py").is_file()
    assert (federated / "publication.py").is_file()
    assert "polars" not in _imported_modules(federated / "contracts.py")
    assert "polars" not in _imported_modules(federated / "publication.py")

    stale_importers = tuple(
        path.relative_to(_SOURCE_ROOT)
        for path in _SOURCE_ROOT.rglob("*.py")
        if "datp_core.evaluation.population" in _imported_modules(path)
    )
    assert stale_importers == ()
