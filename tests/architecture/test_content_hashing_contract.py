import ast
from pathlib import Path

import pytest


@pytest.mark.architecture
def test_content_hashing_exposes_only_explicit_algorithm_specific_functions() -> None:
    module_path = Path("src/datp_core/infrastructure/persistence/hashing.py")
    module = ast.parse(module_path.read_text())
    public_functions = tuple(
        node
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_")
    )

    assert {function.name for function in public_functions} == {
        "blake3_bytes_content_hash",
        "blake3_chunks_content_hash",
        "blake3_file_content_hash",
        "sha256_bytes_content_hash",
        "sha256_file_content_hash",
    }
    assert all("algorithm" not in _parameter_names(function) for function in public_functions)


def _parameter_names(function: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    return {argument.arg for argument in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs)}
