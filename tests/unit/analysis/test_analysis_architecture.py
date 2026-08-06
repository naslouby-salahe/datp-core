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


def test_analysis_separates_decisions_documents_and_preparation() -> None:
    analysis = _SOURCE_ROOT / "analysis"

    assert not (analysis / "decisions.py").exists()
    assert (analysis / "scientific_decision.py").is_file()
    assert (analysis / "documents.py").is_file()
    assert (analysis / "preparation.py").is_file()

    stale_importers = tuple(
        path.relative_to(_SOURCE_ROOT)
        for path in _SOURCE_ROOT.rglob("*.py")
        if "datp_core.analysis.decisions" in _imported_modules(path)
    )
    assert stale_importers == ()

    preparation_source = (analysis / "preparation.py").read_text(encoding="utf-8")
    assert "model_rebuild" not in preparation_source
    assert "TYPE_CHECKING" not in preparation_source
