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
        path.relative_to(_SOURCE_ROOT) for path in _SOURCE_ROOT.rglob("*.py") if module in _imported_modules(path)
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
    assert (execution / "score_generation.py").is_file()


def test_fixed_score_controls_have_bounded_owners_without_a_facade() -> None:
    evaluation = _SOURCE_ROOT / "evaluation"
    fixed_score = evaluation / "fixed_score"
    assert not (evaluation / "controls.py").exists()
    assert (fixed_score / "contracts.py").is_file()
    assert (fixed_score / "checksums.py").is_file()
    assert (fixed_score / "construction.py").is_file()
    assert (fixed_score / "validation.py").is_file()
    assert _source_importers("datp_core.evaluation.controls") == ()


def test_threshold_estimation_math_does_not_read_artifacts() -> None:
    evaluation = _SOURCE_ROOT / "evaluation"
    diagnostics = evaluation / "threshold_estimation.py"
    evidence = evaluation / "threshold_evidence.py"
    assert evidence.is_file()
    imported = _imported_modules(diagnostics)
    assert "polars" not in imported
    assert "datp_core.protocols.inference" not in imported
    assert all(not module.startswith("datp_core.runtime") for module in imported)
    assert "checksum_file" not in diagnostics.read_text(encoding="utf-8")


def test_evaluation_cohorts_have_separate_contract_classification_and_evidence_owners() -> None:
    evaluation = _SOURCE_ROOT / "evaluation"
    cohort = evaluation / "cohort"
    assert not (evaluation / "cohorts.py").exists()
    assert (cohort / "contracts.py").is_file()
    assert (cohort / "construction.py").is_file()
    assert (cohort / "evidence.py").is_file()
    assert _source_importers("datp_core.evaluation.cohorts") == ()
    assert "polars" not in _imported_modules(cohort / "construction.py")


def test_protocol_declaration_hub_is_deleted_and_has_no_callers() -> None:
    assert not (_SOURCE_ROOT / "protocols" / "models.py").exists()
    assert _source_importers("datp_core.protocols.models") == ()


def test_domain_values_hub_is_decomposed_into_focused_modules() -> None:
    values = _SOURCE_ROOT / "domain" / "values"
    assert not (_SOURCE_ROOT / "domain" / "values.py").exists()
    assert values.is_dir()
    for name in ("base", "counts", "ratios", "identifiers", "paths", "checksums"):
        assert (values / f"{name}.py").is_file()
    assert _source_importers("datp_core.domain.values") == ()


def test_domain_enums_no_longer_declares_relocated_package_identities() -> None:
    enums = _SOURCE_ROOT / "domain" / "enums.py"
    declared = tuple(node.name for node in _syntax_tree(enums).body if isinstance(node, ClassDef))
    relocated = (
        "ClaimStatus",
        "ScientificDecision",
        "WarningCode",
        "PreprocessingFitScope",
        "TrustedEstimatorClassName",
        "PartitionOrdering",
        "ControlledPartitionKind",
        "CapabilityStatus",
        "ConfirmatoryDeltaDirection",
        "ClusterFingerprintFeature",
        "ClusterFeatureStandardization",
        "ClusterAssignmentAlgorithm",
        "KMeansInitialization",
        "ClusterThresholdAggregation",
    )
    assert not (set(declared) & set(relocated))


def test_preprocessing_service_delegates_client_and_artifact_responsibilities() -> None:
    preprocessing = _SOURCE_ROOT / "preprocessing"
    assert (preprocessing / "client_partitions.py").is_file()
    assert (preprocessing / "ciciot_file_clients.py").is_file()
    assert (preprocessing / "persisted_artifacts.py").is_file()
    service = preprocessing / "service.py"
    service_text = service.read_text(encoding="utf-8")
    assert "_load_published_population_split" not in service_text
    assert "_preprocess_ciciot_client_local" not in service_text
    assert "_ciciot_source_files" not in service_text


def test_stale_monolithic_cli_run_module_is_removed() -> None:
    assert not (_SOURCE_ROOT / "cli" / "run.py").exists()
    assert _source_importers("datp_core.cli.run") == ()


def test_legacy_orchestration_package_is_removed() -> None:
    assert not (_SOURCE_ROOT / "orchestration").exists()
    assert _source_importers("datp_core.orchestration") == ()


def test_analysis_documents_module_remains_deleted() -> None:
    assert not (_SOURCE_ROOT / "analysis" / "documents.py").exists()
    assert _source_importers("datp_core.analysis.documents") == ()


def test_absorption_and_mechanism_helpers_have_production_callers() -> None:
    mechanisms_importers = _source_importers("datp_core.analysis.mechanisms")
    assert any(path.parts[0] == "pipeline" for path in mechanisms_importers)
    personalization = (_SOURCE_ROOT / "pipeline" / "workflows" / "personalization.py").read_text(encoding="utf-8")
    assert "decide_absorption_cohort" in personalization
    personalization_cli = (_SOURCE_ROOT / "cli" / "personalization.py").read_text(encoding="utf-8")
    assert "analyze-ditto-absorption" in personalization_cli
    assert "analyze-fedprox-absorption" in personalization_cli
    assert "load_fedavg_cv_fpr_effect" in personalization_cli
