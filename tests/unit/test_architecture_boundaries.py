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


def _source_importers(module: str) -> tuple[Path, ...]:
    return tuple(
        path.relative_to(_SOURCE_ROOT)
        for path in _SOURCE_ROOT.rglob("*.py")
        if module in _imported_modules(path)
    )


def test_deleted_protocol_runtime_has_no_callers() -> None:
    assert _source_importers("datp_core.protocols.runtime") == ()


def test_partition_contracts_do_not_depend_on_runtime_configuration() -> None:
    contracts = _SOURCE_ROOT / "datasets" / "partitioning" / "contracts.py"
    assert all(not module.startswith("datp_core.runtime") for module in _imported_modules(contracts))


def test_pipeline_preparation_does_not_redefine_dataset_or_preprocessing_services() -> None:
    preparation = _SOURCE_ROOT / "pipeline" / "preparation"
    assert not (preparation / "datasets.py").exists()
    assert not (preparation / "preprocessing.py").exists()
    assert _source_importers("datp_core.pipeline.preparation.datasets") == ()
    assert _source_importers("datp_core.pipeline.preparation.preprocessing") == ()


def test_global_federated_algorithms_use_one_public_training_module() -> None:
    federated = _SOURCE_ROOT / "learning" / "federated"
    assert not (federated / "fedavg.py").exists()
    assert not (federated / "fedprox.py").exists()
    assert (federated / "global_training.py").is_file()
