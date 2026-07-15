import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE_ROOT = Path("src/datp_core")


@pytest.mark.architecture
def test_modules_have_no_top_level_runtime_call_expression() -> None:
    assert not _top_level_runtime_calls(SOURCE_ROOT)


@pytest.mark.architecture
def test_module_imports_do_not_construct_threads_or_processes() -> None:
    assert not _top_level_process_constructors(SOURCE_ROOT)


@pytest.mark.architecture
def test_importing_the_complete_package_has_no_python_process_or_thread_side_effects(tmp_path: Path) -> None:
    module_names = tuple(_module_name(path) for path in SOURCE_ROOT.rglob("*.py"))
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYTHONPATH"] = str(SOURCE_ROOT.parent.resolve())
    program = (
        "import importlib\n"
        "import threading\n"
        f"module_names = {module_names!r}\n"
        "before = tuple(thread.name for thread in threading.enumerate())\n"
        "for module_name in module_names:\n"
        "    importlib.import_module(module_name)\n"
        "after = tuple(thread.name for thread in threading.enumerate())\n"
        "assert after == before, (before, after)\n"
    )
    completed = subprocess.run(
        (sys.executable, "-c", program),
        check=False,
        capture_output=True,
        cwd=tmp_path,
        env=environment,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr


def test_side_effect_scan_rejects_an_adversarial_import_time_thread(tmp_path: Path) -> None:
    module = tmp_path / "bad.py"
    module.write_text("Thread()\n")

    assert _top_level_runtime_calls(tmp_path) == ((module, 1),)


def _top_level_runtime_calls(root: Path) -> tuple[tuple[Path, int], ...]:
    violations: list[tuple[Path, int]] = []
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text())
        for node in tree.body:
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                violations.append((path, node.lineno))
    return tuple(violations)


def _top_level_process_constructors(root: Path) -> tuple[tuple[Path, int], ...]:
    return tuple((path, node.lineno) for path in root.rglob("*.py") for node in _process_constructor_nodes(path))


def _process_constructor_nodes(path: Path) -> tuple[ast.stmt, ...]:
    return tuple(node for node in ast.parse(path.read_text()).body if _is_process_constructor(node))


def _is_process_constructor(node: ast.stmt) -> bool:
    return isinstance(node, ast.Assign) and _is_named_process_constructor(node.value)


def _is_named_process_constructor(value: ast.expr) -> bool:
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id
        in {
            "Thread",
            "Process",
            "Pool",
            "Executor",
        }
    )


def _module_name(path: Path) -> str:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = relative.parts[:-1] if relative.name == "__init__" else relative.parts
    return ".".join(("datp_core", *parts))
