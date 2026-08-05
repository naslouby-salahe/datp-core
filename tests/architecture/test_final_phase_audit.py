import ast
import re
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
SOURCE_ROOT = REPOSITORY_ROOT / "src" / "datp_core"
GENERATED_SUFFIXES = {".log", ".trace", ".traceback", ".prof", ".coverage", ".pyc"}
UNSAFE_PERSISTENCE_MODULES = {"pickle", "joblib", "cloudpickle", "dill"}
OPAQUE_POLICY_IDENTITY = re.compile(r"(?<![A-Za-z0-9_])B[0-4](?![A-Za-z0-9_])")


def _source_files() -> tuple[Path, ...]:
    return tuple(sorted(path for path in SOURCE_ROOT.rglob("*.py") if "__pycache__" not in path.parts))


def _tracked_source_paths() -> tuple[Path, ...]:
    completed = subprocess.run(
        ("git", "ls-files", "src/datp_core"),
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(REPOSITORY_ROOT / relative for relative in completed.stdout.splitlines() if relative)


def test_source_tree_contains_no_generated_or_runtime_artifacts() -> None:
    violations = tuple(
        str(path.relative_to(REPOSITORY_ROOT))
        for path in _tracked_source_paths()
        if path.suffix in GENERATED_SUFFIXES
        or path.name in {"COMPLETE", ".coverage"}
        or path.name.endswith(("~", ".tmp", ".bak"))
    )
    assert not violations, "\n".join(violations)


def test_source_never_imports_unsafe_object_serializers() -> None:
    violations: list[str] = []
    for path in _source_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imported: tuple[str, ...] = ()
            if isinstance(node, ast.Import):
                imported = tuple(alias.name.split(".", maxsplit=1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported = (node.module.split(".", maxsplit=1)[0],)
            for module in imported:
                if module in UNSAFE_PERSISTENCE_MODULES:
                    violations.append(f"{path.relative_to(REPOSITORY_ROOT)} imports {module}")
    assert not violations, "\n".join(violations)


def test_current_implementation_contains_no_numbered_threshold_identity() -> None:
    violations = tuple(
        str(path.relative_to(REPOSITORY_ROOT))
        for path in _source_files()
        if OPAQUE_POLICY_IDENTITY.search(path.read_text(encoding="utf-8"))
    )
    assert not violations, "\n".join(violations)
