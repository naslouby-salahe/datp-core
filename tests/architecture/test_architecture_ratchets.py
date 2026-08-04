import ast
import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "datp_core"
PIPELINE_ROOT = SOURCE_ROOT / "pipeline"

SERIALIZATION_BYPASS_BASELINE = frozenset(
    {
        Path("src/datp_core/datasets/canonical_cache.py"),
        Path("src/datp_core/domain/provenance.py"),
        Path("src/datp_core/learning/federated/checkpointing.py"),
        Path("src/datp_core/preprocessing/validation.py"),
    }
)
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
CANONICAL_THRESHOLD_TOKEN = re.compile(r"\bB[0-4]\b")


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


def _contains_any_annotation(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Name) and node.id == "Any"
        for node in ast.walk(tree)
    )


def _uses_serialization_bypass(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr in {"dumps", "model_dump_json"}:
            return True
    return False


def test_pipeline_is_branch_neutral_and_strictly_typed() -> None:
    violations: list[str] = []
    for path in _python_files(PIPELINE_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for imported in _module_imports(tree):
            if any(imported == root or imported.startswith(f"{root}.") for root in FORBIDDEN_PIPELINE_IMPORT_ROOTS):
                violations.append(f"{path.relative_to(REPOSITORY_ROOT)} imports {imported}")
        if _contains_any_annotation(tree):
            violations.append(f"{path.relative_to(REPOSITORY_ROOT)} uses Any")
    assert not violations, "\n".join(violations)


def test_serialization_bypass_cannot_expand() -> None:
    observed = frozenset(
        path.relative_to(REPOSITORY_ROOT)
        for path in _python_files(SOURCE_ROOT)
        if path != SOURCE_ROOT / "artifacts" / "serialization.py"
        and _uses_serialization_bypass(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    )
    assert observed <= SERIALIZATION_BYPASS_BASELINE, (
        "direct JSON serialization must remain inside artifacts/serialization.py; "
        f"new bypasses: {sorted(observed - SERIALIZATION_BYPASS_BASELINE)}"
    )


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
