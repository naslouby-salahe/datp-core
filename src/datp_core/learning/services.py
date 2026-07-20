"""Framework-independent checkpoint selection guards against test-driven selection."""

from __future__ import annotations


def select_checkpoint_round(candidates: tuple[tuple[int, float], ...]) -> int:
    """Select the earliest scheduled round with the lowest benign calibration loss."""
    if not candidates:
        raise ValueError("at least one scheduled checkpoint candidate is required")
    if any(round_number <= 0 or loss < 0.0 or loss != loss for round_number, loss in candidates):
        raise ValueError("checkpoint candidates must contain positive rounds and finite non-negative benign losses")
    return min(candidates, key=lambda item: (item[1], item[0]))[0]
