"""Conformance: authored configuration models never leak outside the configuration boundary.

Authored Pydantic models (``datp_core.config.schema.*``) may only be imported by the
configuration layer itself, which is solely responsible for resolving every authored value into
a pure, Pydantic-free domain record before it crosses into any other feature package.
"""

from __future__ import annotations

from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[3] / "src" / "datp_core"
_MARKER = "datp_core.config.schema"

# Files permitted to import authored configuration (Pydantic) models.
_ALLOWLIST = {
    "config/project.py",
    "config/loading.py",
    "config/fingerprints.py",
    "config/resolve/datasets.py",
    "config/resolve/experiments.py",
    "config/resolve/protocols.py",
    "config/resolve/runtime.py",
    "config/schema/__init__.py",
    "config/schema/datasets.py",
    "config/schema/experiments.py",
    "config/schema/protocols.py",
    "config/schema/runtime.py",
}


def _relative(path: Path) -> str:
    return path.relative_to(_SRC_ROOT).as_posix()


def test_authored_config_models_only_imported_by_allowlisted_modules() -> None:
    offenders: list[str] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        relative = _relative(path)
        if relative in _ALLOWLIST:
            continue
        # Intra-model imports within config/ are always permitted.
        if relative.startswith("config/"):
            continue
        if _MARKER in path.read_text(encoding="utf-8"):
            offenders.append(relative)
    assert offenders == [], f"Authored config models leaked into: {offenders}"


def test_allowlisted_modules_still_exist() -> None:
    # Guards against the allowlist silently drifting from reality.
    for relative in _ALLOWLIST:
        assert (_SRC_ROOT / relative).exists(), f"Allowlisted module missing: {relative}"
