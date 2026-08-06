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


def test_bootstrap_inference_separates_contracts_validation_and_estimation() -> None:
    inference = _SOURCE_ROOT / "analysis" / "inference"
    bootstrap = inference / "bootstrap"

    assert not (inference / "bootstrap.py").exists()
    assert (bootstrap / "contracts.py").is_file()
    assert (bootstrap / "validation.py").is_file()
    assert (bootstrap / "estimation.py").is_file()

    assert "numpy" not in _imported_modules(bootstrap / "contracts.py")
    assert "scipy" not in _imported_modules(bootstrap / "contracts.py")
    assert "numpy" not in _imported_modules(bootstrap / "validation.py")
    assert "scipy" not in _imported_modules(bootstrap / "validation.py")

    stale_importers = tuple(
        path.relative_to(_SOURCE_ROOT)
        for path in _SOURCE_ROOT.rglob("*.py")
        if "datp_core.analysis.inference.bootstrap" in _imported_modules(path)
    )
    assert stale_importers == ()
