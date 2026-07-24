from __future__ import annotations

from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "datp_core"

_EXPECTED_PACKAGES = (
    "analysis",
    "artifacts",
    "config",
    "contracts",
    "core",
    "data",
    "evaluation",
    "experiments",
    "learning",
    "pipeline",
    "reporting",
    "thresholding",
)


def test_expected_source_packages_exist() -> None:
    missing = [pkg for pkg in _EXPECTED_PACKAGES if not (_SRC_ROOT / pkg / "__init__.py").exists()]
    assert missing == [], f"Missing source packages: {missing}"


def test_resolved_configuration_module_is_present() -> None:
    assert (_SRC_ROOT / "config" / "project.py").exists()
    assert (_SRC_ROOT / "app.py").exists()
