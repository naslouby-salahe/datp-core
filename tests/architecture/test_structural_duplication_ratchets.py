import ast
from collections import defaultdict
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "datp_core"
POPULATION_MODELS = SOURCE_ROOT / "populations" / "models.py"

AUDITED_STRUCTURAL_ROOTS = (
    SOURCE_ROOT / "pipeline",
    SOURCE_ROOT / "centralized_reference",
    SOURCE_ROOT / "scoring",
    SOURCE_ROOT / "learning" / "federated" / "checkpoints",
    SOURCE_ROOT / "analysis",
)
INTENTIONAL_DUPLICATE_SHAPES = frozenset(
    {
        frozenset({"PooledScoreArtifact", "ScoreRecord"}),
    }
)
LEGACY_PRIMITIVE_LEAKAGE_PATHS = frozenset(
    {
        Path("src/datp_core/datasets/models.py"),
        Path("src/datp_core/populations/models.py"),
        Path("src/datp_core/protocols/models.py"),
        Path("src/datp_core/thresholding/models.py"),
    }
)
SEMANTIC_PRIMITIVE_FIELDS = {
    "client_id": {"str"},
    "stable_id": {"str"},
    "seed": {"int"},
    "training_seed": {"int"},
    "round_number": {"int"},
    "threshold": {"float"},
    "row_count": {"int"},
}
GENERIC_MODULE_NAMES = frozenset(
    {"models.py", "values.py", "enums.py", "utils.py", "helpers.py"}
)
MAX_NEW_GENERIC_MODULE_LINES = 700
LEGACY_LARGE_GENERIC_MODULES = frozenset(
    {
        Path("src/datp_core/domain/enums.py"),
        Path("src/datp_core/domain/values.py"),
        Path("src/datp_core/datasets/models.py"),
        Path("src/datp_core/populations/models.py"),
        Path("src/datp_core/protocols/models.py"),
        Path("src/datp_core/thresholding/models.py"),
    }
)


def _python_files(root: Path) -> tuple[Path, ...]:
    return tuple(
        sorted(
            path
            for path in root.rglob("*.py")
            if "__pycache__" not in path.parts
        )
    )


def _class_fields(node: ast.ClassDef) -> tuple[tuple[str, str], ...]:
    fields: list[tuple[str, str]] = []
    for statement in node.body:
        if (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
        ):
            fields.append(
                (statement.target.id, ast.unparse(statement.annotation))
            )
    return tuple(fields)


def _class_node(path: Path, class_name: str) -> ast.ClassDef:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )
    assert len(matches) == 1, f"expected one {class_name} in {path}"
    return matches[0]


def _is_structural_model(node: ast.ClassDef) -> bool:
    decorators = {
        ast.unparse(decorator).split("(")[0]
        for decorator in node.decorator_list
    }
    bases = {ast.unparse(base).split(".")[-1] for base in node.bases}
    return "dataclass" in decorators or "StrictModel" in bases


def test_structural_model_shapes_are_not_reimplemented_in_audited_packages() -> None:
    shapes: dict[tuple[tuple[str, str], ...], list[str]] = defaultdict(list)
    for root in AUDITED_STRUCTURAL_ROOTS:
        for path in _python_files(root):
            tree = ast.parse(
                path.read_text(encoding="utf-8"),
                filename=str(path),
            )
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and _is_structural_model(node):
                    fields = _class_fields(node)
                    if fields:
                        shapes[fields].append(node.name)
    violations = []
    for names in shapes.values():
        if len(names) < 2:
            continue
        name_set = frozenset(names)
        if name_set not in INTENTIONAL_DUPLICATE_SHAPES:
            violations.append(tuple(sorted(names)))
    assert not violations, (
        "duplicate structural model shapes require consolidation or review: "
        f"{violations}"
    )


def test_client_partition_counts_reuses_canonical_client_identity() -> None:
    fields = dict(_class_fields(_class_node(POPULATION_MODELS, "ClientPartitionCounts")))
    assert fields.get("client") == "ClientIdentity"
    assert "client_id" not in fields


def test_semantic_primitive_leakage_cannot_expand_beyond_legacy_model_warehouses() -> None:
    violations: list[str] = []
    observed_paths: set[Path] = set()
    for path in _python_files(SOURCE_ROOT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                not isinstance(node, ast.AnnAssign)
                or not isinstance(node.target, ast.Name)
            ):
                continue
            allowed_primitives = SEMANTIC_PRIMITIVE_FIELDS.get(node.target.id)
            if allowed_primitives is None:
                continue
            annotation = ast.unparse(node.annotation)
            if annotation in allowed_primitives:
                relative = path.relative_to(REPOSITORY_ROOT)
                observed_paths.add(relative)
                if relative not in LEGACY_PRIMITIVE_LEAKAGE_PATHS:
                    violations.append(
                        f"{relative}:{node.target.id}: {annotation}"
                    )
    assert not violations, "\n".join(violations)
    assert observed_paths <= LEGACY_PRIMITIVE_LEAKAGE_PATHS


def test_new_generic_modules_remain_small_and_single_purpose() -> None:
    violations: list[str] = []
    for path in _python_files(SOURCE_ROOT):
        if path.name not in GENERIC_MODULE_NAMES:
            continue
        relative = path.relative_to(REPOSITORY_ROOT)
        line_count = len(path.read_text(encoding="utf-8").splitlines())
        if (
            relative not in LEGACY_LARGE_GENERIC_MODULES
            and line_count > MAX_NEW_GENERIC_MODULE_LINES
        ):
            violations.append(f"{relative}: {line_count} lines")
    assert not violations, (
        "new generic modules exceeded the architecture limit:\n"
        + "\n".join(violations)
    )
