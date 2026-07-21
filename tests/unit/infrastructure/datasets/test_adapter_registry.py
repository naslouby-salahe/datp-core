"""Dataset adapter registry registration and missing-adapter error tests."""

from __future__ import annotations

import pytest

from datp_core.composition.root import _build_adapter_registry
from datp_core.domain.datasets import AdapterKind


def test_adapter_registry_contains_nbaiot_and_ciciot2023() -> None:
    """The registry must have adapters for N-BaIoT and CICIoT2023."""
    registry = _build_adapter_registry()
    registered = set(registry.registered_kinds)
    assert AdapterKind.NBAIOT in registered
    assert AdapterKind.CICIOT2023 in registered


def test_adapter_registry_returns_correct_adapter_kind() -> None:
    """Each registered adapter must report its AdapterKind correctly."""
    registry = _build_adapter_registry()
    for kind in registry.registered_kinds:
        adapter = registry.get(kind)
        assert adapter.adapter_kind == kind


def test_adapter_registry_raises_keyerror_for_missing_kind() -> None:
    """Requesting an unregistered AdapterKind must raise KeyError with a descriptive message."""
    registry = _build_adapter_registry()

    with pytest.raises(KeyError, match="No dataset materializer registered for adapter kind"):
        registry.get(AdapterKind.EDGE_IIOTSET)
