from __future__ import annotations

from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "datp_core"

_EXPECTED_PACKAGES = (
    "application",
    "composition",
    "config",
    "config/models",
    "domain",
    "infrastructure",
    "infrastructure/artifacts",
    "infrastructure/datasets",
    "infrastructure/federation",
    "infrastructure/learning",
    "infrastructure/querying",
    "infrastructure/runtime",
    "infrastructure/tables",
    "infrastructure/thresholding",
    "interfaces",
    "planning",
)


def test_expected_source_packages_exist() -> None:
    missing = [pkg for pkg in _EXPECTED_PACKAGES if not (_SRC_ROOT / pkg / "__init__.py").exists()]
    assert missing == [], f"Missing source packages: {missing}"


def test_resolved_configuration_module_is_present() -> None:
    assert (_SRC_ROOT / "config" / "resolver.py").exists()
    assert (_SRC_ROOT / "composition" / "root.py").exists()
