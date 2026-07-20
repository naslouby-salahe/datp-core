"""Conformance: authored configuration models never leak outside the configuration boundary.

Authored Pydantic models (``datp_core.config.models``) may only be imported by the configuration
layer itself and by the single allowlisted threshold-policy consumer (see the implementation
decision log: the strict discriminated ``TypedThresholdPolicyConfig`` is the resolved threshold
contract and is intentionally not duplicated into parallel domain records).
"""

from __future__ import annotations

from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "datp_core"
_MARKER = "datp_core.config.models"

# Files permitted to import authored configuration models.
_ALLOWLIST = {
    "config/resolver.py",
    "config/runtime_settings.py",
    "config/yaml_loader.py",
    "infrastructure/thresholding/base.py",
    "infrastructure/thresholding/estimators.py",
}


def _relative(path: Path) -> str:
    return path.relative_to(_SRC_ROOT).as_posix()


def test_authored_config_models_only_imported_by_allowlisted_modules() -> None:
    offenders: list[str] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        relative = _relative(path)
        if relative in _ALLOWLIST:
            continue
        if _MARKER in path.read_text(encoding="utf-8"):
            offenders.append(relative)
    assert offenders == [], f"Authored config models leaked into: {offenders}"


def test_allowlisted_modules_still_exist() -> None:
    # Guards against the allowlist silently drifting from reality.
    for relative in _ALLOWLIST:
        assert (_SRC_ROOT / relative).exists(), f"Allowlisted module missing: {relative}"
