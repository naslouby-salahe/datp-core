from pathlib import Path

import pytest

SOURCE_ROOT = Path("src/datp_core")
FORBIDDEN_MODULE_NAMES = frozenset({"utils", "helpers", "common", "base", "misc", "shared"})


@pytest.mark.architecture
def test_source_tree_has_no_generic_module_or_package_names() -> None:
    assert not _forbidden_name_paths(SOURCE_ROOT)


@pytest.mark.architecture
def test_no_root_experiments_package_exists() -> None:
    assert not (SOURCE_ROOT / "experiments").exists()


def test_forbidden_name_scan_rejects_an_adversarial_module(tmp_path: Path) -> None:
    module = tmp_path / "utils.py"
    module.write_text("")

    assert _forbidden_name_paths(tmp_path) == (module,)


def _forbidden_name_paths(root: Path) -> tuple[Path, ...]:
    paths = (*root.rglob("*.py"), *(path for path in root.rglob("*") if path.is_dir()))
    return tuple(path for path in paths if path.stem.casefold() in FORBIDDEN_MODULE_NAMES)
