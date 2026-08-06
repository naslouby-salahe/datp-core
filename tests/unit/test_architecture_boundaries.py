from ast import ClassDef, FunctionDef, Import, ImportFrom, parse
from pathlib import Path

_SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src" / "datp_core"


def _syntax_tree(path: Path):
    return parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_modules(path: Path) -> tuple[str, ...]:
    modules: list[str] = []
    for node in _syntax_tree(path).body:
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


def test_thresholding_separates_models_dispatch_and_publication_without_analysis_dependency() -> None:
    thresholding = _SOURCE_ROOT / "thresholding"
    assert not (thresholding / "common.py").exists()
    assert (thresholding / "models.py").is_file()
    assert (thresholding / "publication.py").is_file()
    for path in thresholding.rglob("*.py"):
        assert all(not module.startswith("datp_core.analysis") for module in _imported_modules(path)), path


def test_temporal_deployment_provenance_is_protocol_owned() -> None:
    assert (_SOURCE_ROOT / "protocols" / "temporal.py").is_file()
    assert _source_importers("datp_core.analysis.temporal.TemporalDeploymentProvenance") == ()


def test_workspace_contains_only_the_cached_coordinate_coordinator() -> None:
    workspace = _SOURCE_ROOT / "pipeline" / "execution" / "workspace.py"
    top_level_definitions = tuple(
        node.name for node in _syntax_tree(workspace).body if isinstance(node, (ClassDef, FunctionDef))
    )
    assert top_level_definitions == ("ExperimentWorkspace",)
    execution = workspace.parent
    assert (execution / "context.py").is_file()
    assert (execution / "layout.py").is_file()
    assert (execution / "scoring.py").is_file()


def test_fixed_score_controls_have_bounded_owners_without_a_facade() -> None:
    evaluation = _SOURCE_ROOT / "evaluation"
    fixed_score = evaluation / "fixed_score"
    assert not (evaluation / "controls.py").exists()
    assert (fixed_score / "contracts.py").is_file()
    assert (fixed_score / "checksums.py").is_file()
    assert (fixed_score / "construction.py").is_file()
    assert (fixed_score / "validation.py").is_file()
    assert _source_importers("datp_core.evaluation.controls") == ()
