from dataclasses import dataclass

import pytest
from syrupy.assertion import SnapshotAssertion


@dataclass(frozen=True, slots=True, kw_only=True)
class _PlaceholderShape:
    """Non-scientific placeholder used only to prove the syrupy wiring round-trips."""

    label: str
    count: int


@pytest.mark.golden
def test_placeholder_shape_round_trips(snapshot: SnapshotAssertion) -> None:
    shape = _PlaceholderShape(label="placeholder", count=1)
    assert shape == snapshot
