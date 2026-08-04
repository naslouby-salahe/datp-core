import ast
import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "datp_core"
TEST_ROOT = REPOSITORY_ROOT / "tests"
PIPELINE_ROOT = SOURCE_ROOT / "pipeline"
ORCHESTRATION_STAGE_ROOT = SOURCE_ROOT / "orchestration" / "stages"
ARTIFACT_STORE = SOURCE_ROOT / "artifacts" / "store.py"
LEGACY_CHECKPOINT_MODULE = SOURCE_ROOT / "learning" / "federated" / "checkpointing.py"
LEGACY_CHECKPOINT_IMPORT = "datp_core.learning.federated.checkpointing"
CHECKPOINT_PACKAGE = SOURCE_ROOT / "learning" / "federated" / "checkpoints"
CHECKPOINT_CANDIDATE_MODULE = CHECKPOINT_PACKAGE / "candidates.py"
CHECKPOINT_PUBLICATION_MODULE = CHECKPOINT_PACKAGE / "publication.py"
CHECKPOINT_REUSE_MODULE = CHECKPOINT_PACKAGE / "reuse.py"
CHECKPOINT_OWNERSHIP = (
    (
        CHECKPOINT_CANDIDATE_MODULE,
        frozenset(
            {
                "candidate_tensor_name",
                "persist_checkpoint_tensor",
                "retain_checkpoint_candidates",
                "rebase_checkpoint_candidates",
            }
        ),
    ),
    (
        CHECKPOINT_PUBLICATION_MODULE,
        frozenset(
            {
                "build_manifest",
                "load_manifest",
                "write_manifest",
                "expected_publication_files",
                "publication_digest",
                "write_completion",
                "verify_completion",
                "validate_manifest",
                "stage_personalized_candidates",
                "write_federated_training",
                "write_ditto_training",
            }
        ),
    ),
    (
        CHECKPOINT_REUSE_MODULE,
        frozenset(
            {
                "ReusedGlobalCandidatesRequest",
                "ReusedPersonalizedCandidatesRequest",
                "ReusedFederatedTrainingRequest",
                "ReusedDittoTrainingRequest",
                "validated_global_manifest",
                "validated_personalized_manifest",
                "load_reused_global_candidates",
                "load_reused_personalized_candidates",
                "load_reused_federated_training",
                "load_reused_ditto_training",
            }
        ),
    ),
)
LEGACY_ANALYSIS_MODULES = (
    SOURCE_ROOT / "analysis" / "models.py",
    SOURCE_ROOT / "analysis" / "mechanisms.py",
    SOURCE_ROOT / "analysis" / "inference" / "paired.py",
)
LEGACY_ANALYSIS_IMPORTS = frozenset(
    {
        "datp_core.analysis.models",
        "datp_core.analysis.inference.paired",
    }
)
LEGACY_EXPERIMENT_IDENTITY_MODULE = SOURCE_ROOT / "experiments" / "models.py"
LEGACY_EXPERIMENT_IDENTITY_IMPORT = "datp_core.experiments.models"
ANALYSIS_PACKAGE_INITIALIZER = SOURCE_ROOT / "analysis" / "__init__.py"

SERIALIZATION_BYPASS_BASELINE: frozenset[Path] = frozenset()
FORBIDDEN_PIPELINE_IMPORT_ROOTS = frozenset(
    {
        "datp_core.analysis",
        "datp_core.calibration",
        "datp_core.centralized_reference",
        "datp_core.cli",
        "datp_core.evaluation",
        "datp_core.orchestration",
        "datp_core.reporting",
        "datp_core.scoring",
        "datp_core.thresholding",
    }
)
FORBIDDEN_STAGE_LIBRARY_ROOTS = frozenset(
    {
        "numpy",
        "pandas",
        "polars",
        "scipy",
        "sklearn",
        "statsmodels",
        "torch",
    }
)
NEUTRAL_PUBLICATION_SYMBOLS = frozenset(
    {
        "PublicationOutcome",
        "cleanup_staging_directory",
        "create_staging_directory",
        "publish_atomically",
        "replace_directory",
    }
)
CANONICAL_THRESHOLD_TOKEN = re.compile(r"\bB[0-4]\b")
RUNTIME_PAYLOAD_TYPE_NAMES = frozenset({"DataFrame", "Tensor"})


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts))


def _module_imports(tree: ast.AST) -> tuple[str, ...]:
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    return tuple(imports)


def _top_level_definitions(path: Path) -> frozenset[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return frozenset(
        node.name
        for node in tree.body
        if isinstance(
            node,
            (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
        )
    )


def _contains_any_annotation(tree: ast.AST) -> bool:
    return any(isinstance(node, ast.Name) and node.id == "Any" for node in ast.walk(tree))


def _uses_serialization_bypass(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr == "model_dump_json":
            return True
        if isinstance(function, ast.Name) and function.id == "dumps":
            return True
        if (
            isinstance(function, ast.Attribute)
            and isinstance(function.value, ast.Name)
            and function.value.id == "json"
            and function.attr == "dumps"
        ):
            return True
    return False


def _base_names(class_node: ast.ClassDef) -> frozenset[str]:
    return frozenset(ast.unparse(base).split(".")[-1] for base in class_node.bases)


def _annotation_names(class_node: ast.ClassDef) -> frozenset[str]:
    names: set[str] = set()
    for statement in class_node.body:
        if isinstance(statement, ast.AnnAssign):
            names.update(node.id for node in ast.walk(statement.annotation) if isinstance(node, ast.Name))
    return frozenset(names)


def _is_dataclass(class_node: ast.ClassDef) -> bool:
    return any(
        ast.unparse(decorator).split("(")[0].split(".")[-1] == "dataclass" for decorator in class_node.decorator_list
    )


def test_pipeline_is_branch_neutral_and_strictly_typed() -> None:
    violations: list[str] = []
    for path in _python_files(PIPELINE_ROOT):
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        for imported in _module_imports(tree):
            if any(imported == root or imported.startswith(f"{root}.") for root in FORBIDDEN_PIPELINE_IMPORT_ROOTS):
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)} imports {imported}")
        if _contains_any_annotation(tree):
            violations.append(f"{path.relative_to(REPOSITORY_ROOT)} uses Any")
    assert not violations, "\n".join(violations)


def test_orchestration_stages_remain_thin_composition_only() -> None:
    violations: list[str] = []
    for path in _python_files(ORCHESTRATION_STAGE_ROOT):
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        relative = path.relative_to(REPOSITORY_ROOT)
        for imported in _module_imports(tree):
            root = imported.split(".")[0]
            if root in FORBIDDEN_STAGE_LIBRARY_ROOTS:
                violations.append(f"{relative} imports scientific/runtime library {imported}")
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == "datp_core.domain.values"
                and any(alias.name == "checksum_file" for alias in node.names)
            ):
                violations.append(
                    f"{relative} recomputes a publication checksum instead of using the publication result"
                )
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = _base_names(node)
            if _is_dataclass(node) or bases & {
                "BaseModel",
                "StrictModel",
            }:
                violations.append(f"{relative}:{node.name} defines a domain/persistence model in orchestration")
    assert not violations, "\n".join(violations)


def test_serialization_bypass_is_eliminated() -> None:
    observed = frozenset(
        path.relative_to(REPOSITORY_ROOT)
        for path in _python_files(SOURCE_ROOT)
        if path != SOURCE_ROOT / "artifacts" / "serialization.py"
        and _uses_serialization_bypass(
            ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )
        )
    )
    assert observed == SERIALIZATION_BYPASS_BASELINE, (
        "direct JSON serialization must remain inside artifacts/serialization.py; "
        f"observed bypasses: {sorted(observed)}"
    )


def test_neutral_publication_symbols_are_not_reexported_from_artifacts_store() -> None:
    store_tree = ast.parse(
        ARTIFACT_STORE.read_text(encoding="utf-8"),
        filename=str(ARTIFACT_STORE),
    )
    imported_from_atomic = frozenset(
        alias.name
        for node in ast.walk(store_tree)
        if isinstance(node, ast.ImportFrom) and node.module == "datp_core.pipeline.publication.atomic"
        for alias in node.names
    )
    assert not imported_from_atomic & NEUTRAL_PUBLICATION_SYMBOLS

    violations: list[str] = []
    for path in _python_files(SOURCE_ROOT):
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != "datp_core.artifacts.store":
                continue
            imported = frozenset(alias.name for alias in node.names)
            leaked = imported & NEUTRAL_PUBLICATION_SYMBOLS
            if leaked:
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)} imports {sorted(leaked)}")
    assert not violations, "\n".join(violations)


def test_federated_checkpoint_monolith_and_imports_cannot_return() -> None:
    assert not LEGACY_CHECKPOINT_MODULE.exists()
    assert CHECKPOINT_PACKAGE.is_dir()
    violations: list[str] = []
    for root in (SOURCE_ROOT, TEST_ROOT):
        for path in _python_files(root):
            tree = ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )
            if LEGACY_CHECKPOINT_IMPORT in _module_imports(tree):
                violations.append(str(path.relative_to(REPOSITORY_ROOT)))
    assert not violations, f"legacy checkpointing imports remain in: {violations}"


def test_federated_checkpoint_responsibilities_keep_one_owner() -> None:
    definitions = tuple((path, _top_level_definitions(path)) for path, _symbols in CHECKPOINT_OWNERSHIP)
    violations: list[str] = []
    for owner, expected_symbols in CHECKPOINT_OWNERSHIP:
        owner_definitions = next(observed for path, observed in definitions if path == owner)
        missing = expected_symbols - owner_definitions
        if missing:
            violations.append(f"{owner.relative_to(REPOSITORY_ROOT)} missing {sorted(missing)}")
        for other, other_definitions in definitions:
            if other == owner:
                continue
            duplicated = expected_symbols & other_definitions
            if duplicated:
                violations.append(
                    f"{other.relative_to(REPOSITORY_ROOT)} duplicates "
                    f"{sorted(duplicated)} owned by "
                    f"{owner.relative_to(REPOSITORY_ROOT)}"
                )
    assert not violations, "\n".join(violations)


def test_analysis_aggregate_modules_and_imports_cannot_return() -> None:
    assert all(not path.exists() for path in LEGACY_ANALYSIS_MODULES)
    violations: list[str] = []
    for root in (SOURCE_ROOT, TEST_ROOT):
        for path in _python_files(root):
            imports = _module_imports(
                ast.parse(
                    path.read_text(encoding="utf-8"),
                    filename=str(path),
                )
            )
            leaked = LEGACY_ANALYSIS_IMPORTS.intersection(imports)
            if leaked:
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)} imports {sorted(leaked)}")
    assert not violations, "\n".join(violations)


def test_experiment_identity_compatibility_module_cannot_return() -> None:
    assert not LEGACY_EXPERIMENT_IDENTITY_MODULE.exists()
    violations: list[str] = []
    for root in (SOURCE_ROOT, TEST_ROOT):
        for path in _python_files(root):
            imports = _module_imports(
                ast.parse(
                    path.read_text(encoding="utf-8"),
                    filename=str(path),
                )
            )
            if LEGACY_EXPERIMENT_IDENTITY_IMPORT in imports:
                violations.append(str(path.relative_to(REPOSITORY_ROOT)))
    assert not violations, f"legacy experiment identity imports remain in: {violations}"


def test_analysis_package_initializer_is_not_a_reexport_barrel() -> None:
    tree = ast.parse(
        ANALYSIS_PACKAGE_INITIALIZER.read_text(encoding="utf-8"),
        filename=str(ANALYSIS_PACKAGE_INITIALIZER),
    )
    exported_statements = tuple(
        node
        for node in tree.body
        if isinstance(
            node,
            (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign),
        )
    )
    assert not exported_statements


def test_persisted_documents_use_strict_models_and_runtime_payloads_do_not() -> None:
    violations: list[str] = []
    for path in _python_files(SOURCE_ROOT):
        tree = ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            bases = _base_names(node)
            if "BaseModel" in bases and node.name != "StrictModel":
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.name} inherits BaseModel directly")
            if node.name.endswith("Document") and not (
                "StrictModel" in bases or any(base.endswith(("Document", "Model")) for base in bases)
            ):
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.name} is not a StrictModel document")
            if _annotation_names(node) & RUNTIME_PAYLOAD_TYPE_NAMES and (
                "StrictModel" in bases or "BaseModel" in bases
            ):
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)}:{node.name} serializes a runtime payload")
    assert not violations, "\n".join(violations)


def test_no_canonical_threshold_numbering_in_source() -> None:
    violations = tuple(
        str(path.relative_to(REPOSITORY_ROOT))
        for path in _python_files(SOURCE_ROOT)
        if CANONICAL_THRESHOLD_TOKEN.search(path.read_text(encoding="utf-8"))
    )
    assert not violations, f"canonical threshold numbering remains in: {violations}"


def test_duplicate_import_linter_configuration_is_removed() -> None:
    assert (REPOSITORY_ROOT / ".importlinter").is_file()
    assert not (REPOSITORY_ROOT / "importlinter.ini").exists()
