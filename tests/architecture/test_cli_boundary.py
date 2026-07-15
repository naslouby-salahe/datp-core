import ast
from pathlib import Path

CLI_ROOT = Path("src/datp_core/cli")
FORBIDDEN_MODULE_PREFIXES = ("datp_core.config", "datp_core.infrastructure")
ALLOWED_DATP_IMPORT_PREFIXES = ("datp_core.cli", "datp_core.composition", "datp_core.domain.errors")


def test_cli_has_no_configuration_or_infrastructure_import_and_only_reaches_datp_through_composition_or_errors() -> (
    None
):
    for path in sorted(CLI_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text())
        imports = _imported_modules(tree)
        assert not any(module.startswith(FORBIDDEN_MODULE_PREFIXES) for module in imports)
        assert all(
            module.startswith(ALLOWED_DATP_IMPORT_PREFIXES) for module in imports if module.startswith("datp_core")
        )


def test_cli_neither_constructs_adapters_nor_resolves_filesystem_paths() -> None:
    source = "\n".join(path.read_text() for path in sorted(CLI_ROOT.rglob("*.py")))

    assert "Path(" not in source
    assert ".resolve(" not in source
    assert ".mkdir(" not in source
    assert "infrastructure" not in source


def _imported_modules(tree: ast.Module) -> tuple[str, ...]:
    modules: list[str] = []
    for node in ast.walk(tree):
        match node:
            case ast.Import(names=names):
                modules.extend(alias.name for alias in names)
            case ast.ImportFrom(module=module) if module is not None:
                modules.append(module)
            case _:
                continue
    return tuple(modules)
