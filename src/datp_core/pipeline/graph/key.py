"""Private identity for nodes in one in-memory planning graph."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, order=True)
class GraphNodeKey:
    """Deterministic graph-only key; it is never persisted or used as a path."""

    label: str

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("A graph node key requires a non-empty label")
