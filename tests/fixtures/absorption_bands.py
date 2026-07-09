"""Placeholder absorption-band fixture for later phases (R9, MASTER_TICKET_LOG.md).

Shape only: real bands are pre-specified before P6-T11 runs, not decided here.
"""

from __future__ import annotations


def tiny_absorption_bands() -> tuple[tuple[str, float, float], ...]:
    return (
        ("none", 0.0, 0.1),
        ("partial", 0.1, 0.5),
        ("full", 0.5, 1.0),
    )
