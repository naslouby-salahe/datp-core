from ast import Import, ImportFrom, parse
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "datp_core"


def _imported_modules(path: Path) -> tuple[str, ...]:
    tree = parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: list[str] = []
    for node in tree.body:
        if isinstance(node, ImportFrom) and node.module is not None:
            modules.append(node.module)
        elif isinstance(node, Import):
            modules.extend(alias.name for alias in node.names)
    return tuple(modules)


def test_deleted_protocol_runtime_has_no_callers() -> None:
    offenders = tuple(
        path.relative_to(_SOURCE_ROOT)
        for path in _SOURCE_ROOT.rglob("*.py")
        if "datp_core.protocols.runtime" in _imported_modules(path)
    )
    assert offenders == ()


def test_partition_contracts_do_not_depend_on_runtime_configuration() -> None:
    contracts = _SOURCE_ROOT / "datasets" / "partitioning" / "contracts.py"
    assert all(not module.startswith("datp_core.runtime") for module in _imported_modules(contracts))
