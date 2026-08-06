from ast import Import, ImportFrom, parse
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[4] / "src" / "datp_core"


def _imported_modules(path: Path) -> tuple[str, ...]:
    modules: list[str] = []
    for node in parse(path.read_text(encoding="utf-8"), filename=str(path)).body:
        if isinstance(node, ImportFrom) and node.module is not None:
            modules.append(node.module)
        elif isinstance(node, Import):
            modules.extend(alias.name for alias in node.names)
    return tuple(modules)


def test_execution_scoring_responsibilities_have_distinct_owners() -> None:
    execution = _SOURCE_ROOT / "pipeline" / "execution"

    assert not (execution / "scoring.py").exists()
    assert (execution / "checkpoints.py").is_file()
    assert (execution / "score_generation.py").is_file()
    assert (execution / "matched_reference.py").is_file()
    assert (execution / "evidence.py").is_file()

    stale_importers = tuple(
        path.relative_to(_SOURCE_ROOT)
        for path in _SOURCE_ROOT.rglob("*.py")
        if "datp_core.pipeline.execution.scoring" in _imported_modules(path)
    )
    assert stale_importers == ()
